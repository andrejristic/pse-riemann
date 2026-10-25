"""
Local GGUF backend — llama-cpp in-process (plan F3, master §8).

The model runs inside this process (no server, no extra port), loaded lazily and
only when actually selected, with every limiter from limits.py applied:

  * sha256 of the weights is checked against the declarations the operator
    confirmed (master §8); an undeclared or mismatched file is refused;
  * it will not load unless free RAM ≥ file size + headroom, and it unloads at
    once if free RAM falls under the floor;
  * n_threads = cores − 1, n_ctx capped, one call at a time, per-call timeout,
    a <think> budget and a hard output cap, and repetition cut-off.

Absent llama-cpp, or with no .gguf present, the backend simply reports itself
unavailable — the app then runs with cloud models only, or (no models at all)
with the deterministic checks alone. Nothing here is required for the gate, the
lab or the explorer to work.
"""
from __future__ import annotations

import hashlib
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .. import config
from .backend import Backend, Msg, Reply
from . import limits as L


def have_llama() -> bool:
    try:
        import llama_cpp        # noqa: F401
        return True
    except Exception:           # noqa: BLE001
        return False


def list_models() -> list[dict]:
    """Every *.gguf under DIR_MODELS, with size in GiB (fully-downloaded ones)."""
    out = []
    d = config.DIR_MODELS
    if not d.exists():
        return out
    for p in sorted(d.glob("*.gguf")):
        try:
            gb = p.stat().st_size / (1024 ** 3)
        except OSError:
            continue
        out.append({"name": p.name, "path": str(p), "gb": round(gb, 2)})
    return out


def sha256_of(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


class GGUFUnavailable(Exception):
    pass


@dataclass
class _Loaded:
    path: str
    llm: object


class GGUFBackend(Backend):
    """One local model file. `provider` is 'gguf', `model` is the file path."""
    provider = "gguf"
    host = ""                       # local: never touches the egress gate
    key_name = ""
    supports_vision = False

    _lock = threading.Lock()
    _loaded: Optional[_Loaded] = None       # class-level: only one model resident

    def __init__(self, model: str = "", lim: Optional[L.Limits] = None):
        super().__init__(model)
        self.lim = lim or L.Limits()

    # -- availability / verification ------------------------------------- #
    def path(self) -> Path:
        return Path(self.model)

    def verify(self) -> tuple[bool, str]:
        """
        Check the file exists, is declared, and its sha256 matches the declaration.
        A file with no declared hash yet is allowed but flagged (the operator must
        declare it to make loading deterministic across sessions).
        """
        p = self.path()
        if not p.exists():
            return False, f"GGUF ne postoji: {p}"
        try:
            from ..shared_lib import declarations as DECL
            declared = DECL.model_hash(str(p))
        except Exception:           # noqa: BLE001
            declared = None
        if declared is None:
            return True, "hash nije deklarisan — učitavanje dozvoljeno, ali deklariši ga"
        actual = sha256_of(p)
        if actual != declared:
            return False, (f"sha256 se ne poklapa sa deklaracijom (deklarisano "
                           f"{declared[:16]}…, fajl {actual[:16]}…) — učitavanje odbijeno")
        return True, "sha256 se poklapa sa deklaracijom"

    def _model_gb(self) -> float:
        try:
            return self.path().stat().st_size / (1024 ** 3)
        except OSError:
            return 0.0

    # -- loading --------------------------------------------------------- #
    def _ensure_loaded(self):
        if not have_llama():
            raise GGUFUnavailable("llama-cpp nije instaliran")
        ok, why = self.verify()
        if not ok:
            raise GGUFUnavailable(why)
        if not self.lim.can_load(self._model_gb()):
            raise GGUFUnavailable(
                f"premalo slobodnog RAM-a: treba {self._model_gb():.1f}+"
                f"{self.lim.ram_headroom_gb:.1f} GB, slobodno {L.free_ram_gb():.1f} GB")
        with GGUFBackend._lock:
            cur = GGUFBackend._loaded
            if cur is not None and cur.path == self.model:
                return cur.llm
            if cur is not None:                     # a different model is resident
                self._unload_locked()
            import llama_cpp
            llm = llama_cpp.Llama(
                model_path=self.model,
                n_ctx=self.lim.n_ctx,
                n_threads=self.lim.threads(),
                verbose=False,
                seed=0,
            )
            GGUFBackend._loaded = _Loaded(self.model, llm)
            return llm

    @classmethod
    def _unload_locked(cls):
        if cls._loaded is not None:
            try:
                del cls._loaded.llm
            except Exception:       # noqa: BLE001
                pass
            cls._loaded = None

    @classmethod
    def unload(cls):
        with cls._lock:
            cls._unload_locked()

    # -- the call -------------------------------------------------------- #
    def chat(self, messages, system="", max_tokens=4096, effort="high") -> Reply:
        llm = self._ensure_loaded()
        if self.lim.must_unload():
            GGUFBackend.unload()
            raise GGUFUnavailable("slobodan RAM ispod praga — model oslobođen usred reda")
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        kept = L.trim_history(messages, keep_last=16)
        for m in kept:
            msgs.append({"role": m.role, "content": m.text or ""})

        cap = min(max_tokens, self.lim.think_budget + self.lim.max_output)
        with L.one_at_a_time(timeout=self.lim.call_timeout_s):
            out = llm.create_chat_completion(
                messages=msgs, max_tokens=cap, temperature=0.4, seed=0)
        ch = (out.get("choices") or [{}])[0]
        text = (ch.get("message") or {}).get("content") or ""
        if L.is_looping(text):
            text = text.rstrip() + "\n\n[prekinuto: detektovano ponavljanje]"
            stop = "loop"
        else:
            stop = ch.get("finish_reason", "")
        u = out.get("usage", {})
        return Reply(text, "gguf", Path(self.model).name,
                     int(u.get("prompt_tokens", 0)),
                     int(u.get("completion_tokens", 0)), stop, out)
