"""
Theta — other-directed compute, given a concrete meaning for this app.

In the PSE kernel theta is the share of the unit's compute directed at the OTHER.
Here the "other" is *everything that is not yours*: literature you read, text a
model generated, material the scraper pulled in. The "self" is what this system
and you produce and can stand behind: Lab computations, your own notes and
whiteboard derivations, cards you wrote yourself.

    theta = 100 * other / (other + self)

That makes the number a real instrument for a 20-day study, not decoration:

    theta > 35   the assistant is drowning you in other people's material and
                 parroting the literature; you are consuming, not deriving.
    theta < 25   it is spinning in its own speculation without checking sources.
    sigma < 0.01 schizoid: it stopped engaging and just generates.

Spec §0 constants, §2 THETA-as-health-metric, §3 single-gate rule: every theta
change goes through record(), which is the only writer, and it logs to the journal.
"""
from __future__ import annotations

import json
import statistics
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Optional

from .. import config
from . import journal as J

# Work classified as OTHER-directed
OTHER_KINDS = {
    "model_output",     # tokens a model generated for us
    "source_read",      # characters of external literature ingested
    "scrape",           # material pulled by the ingest process
    "citation",         # a CITED card created from someone else's result
}
# Work classified as SELF-directed
SELF_KINDS = {
    "lab_run",          # a numerical experiment we ran and can reproduce
    "user_write",       # you typing / drawing
    "own_derivation",   # a card you authored
    "verification",     # skeptic pass, gate check, recomputation
}

# Relative weights: one lab run is worth more "self" than one keystroke, one paper
# read is worth more "other" than one chat reply. Units are arbitrary but stable.
KIND_WEIGHT = {
    "model_output": 1.0, "source_read": 2.0, "scrape": 0.5, "citation": 1.5,
    "lab_run": 3.0, "user_write": 1.0, "own_derivation": 2.5, "verification": 1.5,
}


@dataclass
class ThetaState:
    other: float = 0.0
    self_: float = 0.0
    series: Deque[float] = field(default_factory=lambda: deque(maxlen=2000))
    unknown_source_streak: int = 0

    @property
    def current(self) -> float:
        tot = self.other + self.self_
        if tot <= 0:
            return config.THETA_OPTIMAL          # no data yet: report nominal
        return 100.0 * self.other / tot

    @property
    def sigma(self) -> float:
        """Sigma of theta expressed as a FRACTION (spec bands are on 0..1)."""
        if len(self.series) < 3:
            return 0.0
        return statistics.pstdev([t / 100.0 for t in self.series])


class ThetaMeter:
    """The single gate for all theta changes (spec §3 receive_theta_event)."""

    def __init__(self, decay: float = 0.999):
        # Slow exponential decay so a 20-day session reflects recent balance, not
        # day 1 forever. 0.999 per event ~ half-life of ~700 events.
        self.decay = decay
        self.state = ThetaState()
        self._dirty = 0

    def record(self, kind: str, amount: float = 1.0, source: str = "app",
               note: str = "") -> float:
        w = KIND_WEIGHT.get(kind, 1.0) * float(amount)
        self.state.other *= self.decay
        self.state.self_ *= self.decay
        if kind in OTHER_KINDS:
            self.state.other += w
        elif kind in SELF_KINDS:
            self.state.self_ += w
        else:
            # Unknown source: spec flags 3 consecutive unknowns for human review.
            self.state.unknown_source_streak += 1
            if self.state.unknown_source_streak >= 3:
                J.log(J.THETA, "theta", {"reason": "consecutive_unknown_theta_source",
                                         "kind": kind}, verdict="flag")
            return self.state.current
        self.state.unknown_source_streak = 0
        theta = self.state.current
        self.state.series.append(theta)
        J.log(J.THETA, "theta",
              {"kind": kind, "amount": amount, "weight": w, "theta": round(theta, 2),
               "sigma": round(self.state.sigma, 4), "note": note},
              subject=source)
        self._dirty += 1
        if self._dirty >= 5:
            self.save()
            self._dirty = 0
        return theta

    # -- health ------------------------------------------------------------- #
    def health(self) -> dict:
        t, s = self.state.current, self.state.sigma
        lo, hi = config.THETA_HEALTHY
        if t > hi:
            status, msg = "enmeshment", "previše tuđeg materijala — čitaš, ne izvodiš"
        elif t < lo:
            status, msg = "withdrawal", "premalo provjere izvora — spekulacija raste"
        else:
            status, msg = "healthy", "ravnoteža izvor/izvođenje je zdrava"
        schizoid = (len(self.state.series) >= 50 and s < config.SIGMA_SCHIZOID)
        if schizoid:
            status, msg = "schizoid", "θ je previše ravna — sistem je prestao da uči"
        return {"theta": round(t, 2), "sigma": round(s, 4), "status": status,
                "message": msg, "n": len(self.state.series),
                "band": config.THETA_HEALTHY}

    def to_dict(self) -> dict:
        return {"other": self.state.other, "self": self.state.self_,
                "series": list(self.state.series)}

    def load(self, d: dict) -> None:
        self.state.other = float(d.get("other", 0.0))
        self.state.self_ = float(d.get("self", 0.0))
        self.state.series = deque(d.get("series", []), maxlen=2000)

    # -- persistence ------------------------------------------------------- #
    # Theta is a twenty-day measurement, not a per-process one. Without this
    # the ratio resets on every launch and the health reading is meaningless.
    def save(self) -> None:
        try:
            _STORE.parent.mkdir(parents=True, exist_ok=True)
            tmp = _STORE.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.to_dict()), encoding="utf-8")
            tmp.replace(_STORE)
        except OSError:
            pass

    def restore(self) -> None:
        if not _STORE.exists():
            return
        try:
            self.load(json.loads(_STORE.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            pass


_STORE = config.DIR_STATE / "theta.json"
_METER: Optional[ThetaMeter] = None


def meter() -> ThetaMeter:
    global _METER
    if _METER is None:
        _METER = ThetaMeter()
        _METER.restore()
    return _METER


def record(kind: str, amount: float = 1.0, source: str = "app", note: str = "") -> float:
    return meter().record(kind, amount, source, note)
