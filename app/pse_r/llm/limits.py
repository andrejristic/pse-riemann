"""
Limiters for any model, local or cloud (plan F3, master §5 "→ ∞").

A model — especially an 8B GGUF on a 16 GB / 4-core laptop — must never be able
to take the machine down. Every constraint here is mechanical and checked before
and during a call, so a runaway model is paused and freed rather than left to
swap the box to death:

  RAM        do not load if free < model + headroom; unload at once below a floor
  CPU        at most 3 of 4 threads, the process niced down
  context    n_ctx capped (8K); history trimmed to fit
  thinking   a <think> budget plus a hard output cap
  time       a per-call timeout, and exactly one call at a time (a queue lock)
  loops      repetition detection — a model going in circles is cut off
  → ∞        a divergence watchdog (master §5): a watched metric (latency, memory,
             queue length) over the operator's limit L, or rising 3 steps in a
             row, means pause → free → tell the operator. L is set by the operator.

Nothing here imports a model library; it is arithmetic over /proc and short
strings, so it is fully testable without llama-cpp or a GPU.
"""
from __future__ import annotations

import os
import re
import threading
from dataclasses import dataclass, field


def free_ram_gb() -> float:
    """Available RAM in GiB, from /proc/meminfo (MemAvailable). 0.0 if unknown."""
    try:
        with open("/proc/meminfo", encoding="ascii") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) / (1024 * 1024)
    except (OSError, ValueError, IndexError):
        pass
    return 0.0


def cpu_count() -> int:
    return os.cpu_count() or 1


@dataclass
class Limits:
    # RAM (GiB)
    ram_headroom_gb: float = 2.0       # need model_size + this free to load
    ram_floor_gb: float = 1.5          # below this: unload immediately
    # CPU
    reserve_cores: int = 1             # leave at least this many cores for the OS/GUI
    # context / output (tokens)
    n_ctx: int = 8192
    think_budget: int = 1500
    max_output: int = 2000
    # time
    call_timeout_s: float = 120.0
    # cloud
    max_calls: int = 0                 # 0 = unlimited (budget module also caps $)
    # divergence watchdog (master §5, "→ ∞"); L is operator-set per metric
    L_latency_s: float = 90.0
    L_rss_gb: float = 12.0
    L_queue: int = 8

    def threads(self) -> int:
        return max(1, cpu_count() - self.reserve_cores)

    def can_load(self, model_gb: float) -> bool:
        return free_ram_gb() >= model_gb + self.ram_headroom_gb

    def must_unload(self) -> bool:
        return free_ram_gb() < self.ram_floor_gb


# A single global so that, however many callers exist, only one model call runs
# at a time. A second caller waits; it never starts a parallel decode.
_CALL_LOCK = threading.Lock()


class one_at_a_time:
    """Context manager: acquire the single call slot, optionally with a timeout."""

    def __init__(self, timeout: float = 0.0):
        self.timeout = timeout
        self._held = False

    def __enter__(self):
        self._held = _CALL_LOCK.acquire(timeout=self.timeout if self.timeout else -1)
        if not self._held:
            raise TimeoutError("drugi poziv modelu je u toku — red je zauzet")
        return self

    def __exit__(self, *exc):
        if self._held:
            _CALL_LOCK.release()
            self._held = False


# --------------------------------------------------------------------------- #
# repetition detection
# --------------------------------------------------------------------------- #
def is_looping(text: str, min_run: int = 4, min_len: int = 12) -> bool:
    """
    True if the text is going in circles: the same line repeated `min_run`+ times,
    or a tail that is one phrase (len ≥ min_len) duplicated back to back many times.
    """
    if not text:
        return False
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    run, last = 1, None
    for ln in lines:
        if ln == last and len(ln) >= min_len:
            run += 1
            if run >= min_run:
                return True
        else:
            run, last = 1, ln
    # phrase-level: a chunk that repeats immediately, filling the tail
    tail = text[-400:]
    for n in range(min_len, 80):
        chunk = tail[-n:]
        if chunk.strip() and tail.endswith(chunk * min_run):
            return True
    return False


def trim_history(messages: list, keep_last: int) -> list:
    """Keep the most recent `keep_last` messages (context budget). Simple and safe."""
    return messages[-keep_last:] if keep_last and len(messages) > keep_last else list(messages)


# --------------------------------------------------------------------------- #
# divergence watchdog (master §5)
# --------------------------------------------------------------------------- #
def diverging(series: list[float], L: float) -> bool:
    """
    "→ ∞": the metric has crossed the operator's ceiling L, or it has risen three
    steps in a row (a monotone climb is the signature the kernel watches for).
    """
    if not series:
        return False
    if series[-1] > L:
        return True
    if len(series) >= 4:
        a, b, c, d = series[-4:]
        if a < b < c < d:
            return True
    return False


@dataclass
class Watchdog:
    """Tracks one metric's recent history and says when to pull the plug."""
    name: str
    L: float
    history: list = field(default_factory=list)
    window: int = 8

    def observe(self, value: float) -> bool:
        self.history.append(value)
        if len(self.history) > self.window:
            self.history = self.history[-self.window:]
        return diverging(self.history, self.L)
