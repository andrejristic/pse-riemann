"""
Model policy (plan F3, decision 2026-10-25): ONE main AI, plus a skeptic that is
always a DIFFERENT model.

The old role→provider router is replaced by two choices the operator makes:

    MAIN      does every role (math, chat, vision, triage, curate, summarize…)
    SKEPTIC   does ONLY the skeptic role, and must be a different model

Independence is the whole point: a model grading its own output is a weak check;
a different model attacking it is a real one. The two may not be the same model.

A "model id" is either a cloud provider name ("claude", "gemini", "mistral",
"groq") or a local file as "gguf:<filename>". Defaults, when the operator has not
chosen: MAIN = the strongest available (Claude if its key is set), SKEPTIC = a
different available model, preferring a local GGUF (other vendor, free, offline).

Deterministic checks (reproduction test, provenance, gate, source tiers) stay
above every model and are never routed here. If no distinct skeptic is available
the skeptic is "unavailable" and only the deterministic checks attack a claim.
"""
from __future__ import annotations

from typing import Optional

from .. import settings as S
from ..guardian import secrets as SEC
from . import backend as B
from . import gguf as G

CLOUD = ("claude", "gemini", "mistral", "groq")
MAIN_KEY = "ai_main"
SKEPTIC_KEY = "ai_skeptic"

# "Kad birati" — ✓ bolje kada… / ✗ slabije kada… (for the GUI chooser, F6).
GUIDANCE = {
    "claude": {"+": "najjači za matematiku i izvlačenje; plaćen",
               "-": "troši budžet; traži internet"},
    "gemini": {"+": "besplatan tier, vidi slike", "-": "slabiji na dugom dokazu"},
    "mistral": {"+": "besplatan tier, brz", "-": "bez slika; kraći kontekst"},
    "groq": {"+": "vrlo brz, besplatan — dobar za trijažu/skeptika",
             "-": "manji modeli; bez slika"},
    "gguf": {"+": "lokalno, offline, bez troška — idealan drugi glas (skeptik)",
             "-": "sporiji na CPU; troši RAM; slabiji od plaćenog oblaka"},
}


def _vendor(model_id: str) -> str:
    return "gguf" if model_id.startswith("gguf:") else model_id


def cloud_available() -> list[str]:
    s = SEC.store()
    return [p for p in CLOUD if p in B.BACKENDS and s.has(B.BACKENDS[p].key_name)]


def gguf_available() -> list[str]:
    if not G.have_llama():
        return []
    return [f"gguf:{m['name']}" for m in G.list_models()]


def candidates() -> list[dict]:
    """Every model the operator could pick right now, with guidance."""
    out = []
    for p in cloud_available():
        out.append({"id": p, "kind": "cloud", "label": p,
                    "guide": GUIDANCE.get(p, {})})
    for gid in gguf_available():
        out.append({"id": gid, "kind": "gguf", "label": gid,
                    "guide": GUIDANCE["gguf"]})
    return out


def _available_ids() -> list[str]:
    return cloud_available() + gguf_available()


def default_main() -> Optional[str]:
    av = _available_ids()
    for pref in ("claude", "gemini", "mistral", "groq"):
        if pref in av:
            return pref
    return av[0] if av else None


def default_skeptic(main: Optional[str]) -> Optional[str]:
    """A different model from `main`, preferring a local GGUF, then another vendor."""
    av = [m for m in _available_ids() if m != main]
    ggufs = [m for m in av if m.startswith("gguf:")]
    if ggufs:
        return ggufs[0]
    other = [m for m in av if _vendor(m) != _vendor(main or "")]
    return (other or av or [None])[0]


def get_main() -> Optional[str]:
    return S.get(MAIN_KEY) or default_main()


def get_skeptic() -> Optional[str]:
    chosen = S.get(SKEPTIC_KEY)
    main = get_main()
    if chosen and chosen != main:
        return chosen
    return default_skeptic(main)


def set_main(model_id: str) -> None:
    if model_id not in _available_ids():
        raise ValueError(f"model '{model_id}' nije dostupan")
    if model_id == S.get(SKEPTIC_KEY):
        raise ValueError("glavni i skeptik ne smiju biti isti model")
    S.set_(MAIN_KEY, model_id)


def set_skeptic(model_id: str) -> None:
    if model_id not in _available_ids():
        raise ValueError(f"model '{model_id}' nije dostupan")
    if model_id == get_main():
        raise ValueError("skeptik mora biti drugi model od glavnog")
    S.set_(SKEPTIC_KEY, model_id)


def skeptic_available() -> bool:
    sk, main = get_skeptic(), get_main()
    return bool(sk) and sk != main


def backend_for(model_id: str) -> B.Backend:
    """A ready Backend for a model id. Does not load a GGUF until it is called."""
    if model_id.startswith("gguf:"):
        name = model_id.split(":", 1)[1]
        from .. import config
        return G.GGUFBackend(str(config.DIR_MODELS / name))
    return B.make(model_id)


def role_backend(role: str) -> B.Backend:
    """The skeptic role goes to the skeptic model; everything else to the main."""
    mid = get_skeptic() if role == B.SKEPTIC else get_main()
    if not mid:
        raise B_NoModel("nijedan model nije dostupan — podesi ključ ili stavi GGUF")
    return backend_for(mid)


class B_NoModel(Exception):
    pass
