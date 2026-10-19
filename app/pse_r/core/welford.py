"""
Scalar streaming Welford — one pass, numerically stable, mergeable (Chan).

Used for guardian per-source rolling baselines (cadence / egress / inter-arrival
variance) and for theta sigma. Scalar-only and numpy-free on purpose: the guardian
must be importable before anything heavy, and baselines are persisted as plain JSON.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class Welford:
    n: int = 0
    mean: float = 0.0
    M2: float = 0.0

    def update(self, x: float) -> "Welford":
        x = float(x)
        self.n += 1
        delta = x - self.mean
        self.mean += delta / self.n
        self.M2 += delta * (x - self.mean)
        return self

    @property
    def variance(self) -> float:
        return self.M2 / (self.n - 1) if self.n > 1 else 0.0

    @property
    def std(self) -> float:
        return math.sqrt(max(self.variance, 0.0))

    @staticmethod
    def merge(a: "Welford", b: "Welford") -> "Welford":
        if a.n == 0:
            return Welford(b.n, b.mean, b.M2)
        if b.n == 0:
            return Welford(a.n, a.mean, a.M2)
        n = a.n + b.n
        delta = b.mean - a.mean
        mean = a.mean + delta * (b.n / n)
        M2 = a.M2 + b.M2 + delta * delta * (a.n * b.n / n)
        return Welford(n, mean, M2)

    def to_dict(self) -> dict:
        return {"n": self.n, "mean": self.mean, "M2": self.M2}

    @classmethod
    def from_dict(cls, d: dict) -> "Welford":
        return cls(int(d.get("n", 0)), float(d.get("mean", 0.0)), float(d.get("M2", 0.0)))
