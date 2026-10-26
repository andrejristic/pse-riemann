"""
Swing and attractors on a unit's measured θ series [rules 5, 5a, 23; §5, §7].

Δθ is taken per move. Swing strength = RMSSD over the last 30 moves; an acute
change (PAC) is |Δθ| ≥ 5 points; a sweep is the distance between two
consecutive turning points. All values are θ points.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional, Sequence

from . import constants as K


def rmssd(xs: Sequence[float]) -> float:
    d = [b - a for a, b in zip(xs, xs[1:])]
    return math.sqrt(sum(v * v for v in d) / len(d)) if d else 0.0


def acf1(xs: Sequence[float]) -> float:
    n = len(xs)
    if n < 3:
        return 1.0
    m = sum(xs) / n
    den = sum((x - m) ** 2 for x in xs)
    if den == 0:
        return 1.0
    return sum((xs[i] - m) * (xs[i + 1] - m) for i in range(n - 1)) / den


def sweeps(xs: Sequence[float]) -> list[float]:
    """Distances between consecutive turning points (local extrema)."""
    turns = [xs[0]] if xs else []
    for i in range(1, len(xs) - 1):
        if (xs[i] - xs[i - 1]) * (xs[i + 1] - xs[i]) < 0:
            turns.append(xs[i])
    if len(xs) > 1:
        turns.append(xs[-1])
    return [abs(b - a) for a, b in zip(turns, turns[1:])]


@dataclass
class SwingReport:
    attractor: str
    delta: float
    pac: bool
    sigma: float                 # RMSSD over the swing window
    acf1: float
    mean_long: float
    sweep: float
    reasons: list[str] = field(default_factory=list)
    moves: int = 0

    def as_dict(self) -> dict:
        return {"attractor": self.attractor, "delta": round(self.delta, 2),
                "pac": self.pac, "sigma": round(self.sigma, 3),
                "acf1": round(self.acf1, 3), "mean_long": round(self.mean_long, 2),
                "sweep": round(self.sweep, 2), "reasons": self.reasons,
                "moves": self.moves}


def assess(series: Sequence[float], boundary_empty: bool = False) -> SwingReport:
    """Read the attractor from a unit's θ series (thresholds of rule 5a)."""
    n = len(series)
    delta = series[-1] - series[-2] if n >= 2 else 0.0
    win = list(series[-K.WIN_SWING:])
    longw = list(series[-K.WIN_LONG:])
    sigma = rmssd(win)
    a1 = acf1(win)
    mean_long = sum(longw) / len(longw) if longw else K.THETA_NOM
    sw = sweeps(win)
    last_sweep = sw[-1] if sw else 0.0
    rep = SwingReport(K.HEALTHY, delta, abs(delta) >= K.PAC_POINTS, sigma, a1,
                      mean_long, last_sweep, moves=n)
    if n < 3:
        return rep

    # borderline: swings too large
    if sigma > K.BORDERLINE_SIGMA and a1 < K.BORDERLINE_ACF1:
        rep.reasons.append(f"σ={sigma:.2f} > {K.BORDERLINE_SIGMA} i ACF(1)={a1:.2f} < {K.BORDERLINE_ACF1}")
    if last_sweep > K.AMPLITUDE:
        rep.reasons.append(f"zamah {last_sweep:.1f} > amplitude {K.AMPLITUDE}")
    if len(sw) >= 4 and sw[-1] > sw[-2] > sw[-3] > sw[-4]:
        rep.reasons.append("zamah raste 3 puta zaredom")
    if rep.reasons:
        rep.attractor = K.BORDERLINE
        return rep

    # level attractors need a calm series (σ < 2) over the swing window
    if n >= K.WIN_SWING and sigma < K.LEVEL_SIGMA:
        recent = sum(win) / len(win)
        if mean_long > K.CODEP_MEAN or recent > K.CODEP_SUSTAINED:
            rep.attractor = K.CODEPENDENT
            rep.reasons.append(f"prosjek {mean_long:.1f} iznad 33 uz σ < 2")
            return rep
        if mean_long < K.NARC_MEAN or recent < K.NARC_SUSTAINED:
            rep.attractor = K.NARCISSISTIC
            rep.reasons.append(f"prosjek {mean_long:.1f} ispod 27 uz σ < 2")
            return rep

    # schizoid: swings too small over the long window + empty boundary
    if n < K.SCHIZOID_MIN_MOVES:
        if n >= K.WIN_SWING and sigma < K.SCHIZOID_SIGMA and boundary_empty:
            rep.reasons.append("šizoidni prag: nedovoljno istorije")
        return rep
    long_sigma = rmssd(longw)
    if long_sigma < K.SCHIZOID_SIGMA and boundary_empty:
        rep.attractor = K.SCHIZOID
        rep.reasons.append(f"σ={long_sigma:.2f} < 1 kroz dugi prozor + prazna granica")
    return rep


def healthy_band(theta: float) -> bool:
    return abs(theta - K.THETA_NOM) <= K.THETA_BAND


def last_or(series: Sequence[float], default: Optional[float] = None) -> float:
    return series[-1] if series else (K.THETA_NOM if default is None else default)
