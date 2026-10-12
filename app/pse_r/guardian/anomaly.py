"""
Anomaly scoring — spec §10, adapted from a server's view of traffic to a client's.

The kernel's Guardian watches inbound sources. We are a client on somebody else's
network, so the sources we register are the HOSTS WE TALK TO, and the question
flips: not "is this actor attacking me" but "is this endpoint still the endpoint
I think it is, and is my own traffic to it behaving the way it should".

The seven axes survive the flip almost unchanged:

  connection_cadence   we suddenly hammer a host  -> a loop went wild, or something
                       is driving us
  endpoint_spread      we touch many distinct paths on one host -> scan-like
  payload_entropy      a response that should be JSON/HTML looks like ciphertext
                       or a packed blob -> not what this API returns
  auth_failure_rate    401/403 climbing -> key revoked, or we are talking to an
                       impostor that cannot decrypt our credential
  privesc_attempts     policy violations: writes attempted outside the vault,
                       redirects to non-allowlisted hosts, key material heading to
                       an anonymous host
  egress_volume        outbound bytes above baseline -> exfiltration shape
  timing_regularity    INVERTED, the schizoid paradox: traffic that is TOO regular
                       is automated. A human studying zeta is bursty.

Baselines are per-host rolling Welford triples persisted as JSON, so they survive
restarts (spec §3: baselines live in SHARED_LIB, not in the unit).
"""
from __future__ import annotations

import json
import math
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .. import config
from ..core.welford import Welford


def clamp01(x: float) -> float:
    return 0.0 if x < 0 else (1.0 if x > 1 else float(x))


def zscore_to_unit(x: float, mean: float, std: float) -> float:
    """|z|/3 clipped to [0,1]: 3 sigma above baseline reads as fully anomalous."""
    if std <= 1e-9:
        return 0.0 if abs(x - mean) < 1e-9 else 0.5
    return clamp01(abs(x - mean) / (3.0 * std))


def shannon_entropy(data: bytes, sample: int = 4096) -> float:
    """Bits per byte of a prefix. 8.0 = uniformly random (encrypted/compressed)."""
    b = data[:sample]
    if not b:
        return 0.0
    counts = [0] * 256
    for x in b:
        counts[x] += 1
    n = len(b)
    return -sum((c / n) * math.log2(c / n) for c in counts if c)


@dataclass
class PacketFeatures:
    """One completed (or refused) request to one host."""
    conns_per_sec: float = 0.0
    distinct_endpoints: int = 1
    shannon_entropy: float = 0.0
    auth_fail: int = 0
    auth_total: int = 1
    privesc_calls: int = 0
    egress_bytes: int = 0
    ingress_bytes: int = 0
    interarrival_var: float = 0.0


@dataclass
class Baseline:
    cadence: Welford = field(default_factory=Welford)
    egress: Welford = field(default_factory=Welford)
    iat: Welford = field(default_factory=Welford)
    endpoints: set = field(default_factory=set)
    last_ts: float = 0.0
    n: int = 0

    @property
    def endpoint_norm(self) -> int:
        return max(len(self.endpoints), 1)

    def to_dict(self) -> dict:
        return {"cadence": self.cadence.to_dict(), "egress": self.egress.to_dict(),
                "iat": self.iat.to_dict(), "endpoints": sorted(self.endpoints)[:200],
                "last_ts": self.last_ts, "n": self.n}

    @classmethod
    def from_dict(cls, d: dict) -> "Baseline":
        b = cls(Welford.from_dict(d.get("cadence", {})),
                Welford.from_dict(d.get("egress", {})),
                Welford.from_dict(d.get("iat", {})),
                set(d.get("endpoints", [])), float(d.get("last_ts", 0.0)),
                int(d.get("n", 0)))
        return b


class BaselineStore:
    """Per-host rolling baselines. Survives Guardian re-instantiation (spec §3)."""

    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path or config.BASELINE_DB)
        self._lock = threading.RLock()
        self._data: dict[str, Baseline] = {}
        self._dirty = 0
        self.load()

    def load(self) -> None:
        if self.path.exists():
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                self._data = {k: Baseline.from_dict(v) for k, v in raw.items()}
            except (json.JSONDecodeError, OSError, TypeError):
                self._data = {}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps({k: v.to_dict() for k, v in self._data.items()},
                                  indent=1), encoding="utf-8")
        tmp.replace(self.path)
        self._dirty = 0

    def get(self, host: str) -> Baseline:
        with self._lock:
            return self._data.setdefault(host, Baseline())

    def update(self, host: str, pf: PacketFeatures, endpoint: str = "") -> None:
        with self._lock:
            b = self.get(host)
            now = time.time()
            if b.last_ts:
                b.iat.update(now - b.last_ts)
            b.last_ts = now
            b.cadence.update(pf.conns_per_sec)
            b.egress.update(pf.egress_bytes)
            if endpoint:
                b.endpoints.add(endpoint)
            b.n += 1
            self._dirty += 1
            if self._dirty >= 10:
                self.save()


_BASE: Optional[BaselineStore] = None


def baselines() -> BaselineStore:
    global _BASE
    if _BASE is None:
        _BASE = BaselineStore()
    return _BASE


def score_anomaly_axes(pf: PacketFeatures, b: Baseline) -> dict:
    """Each axis to [0,1]; higher = more anomalous. timing_regularity INVERTED."""
    s = {}
    s["connection_cadence"] = zscore_to_unit(pf.conns_per_sec, b.cadence.mean,
                                             b.cadence.std)
    s["endpoint_spread"] = clamp01(pf.distinct_endpoints / max(b.endpoint_norm, 1))
    s["payload_entropy"] = clamp01(pf.shannon_entropy / 8.0)
    s["auth_failure_rate"] = clamp01(pf.auth_fail / max(pf.auth_total, 1))
    s["privesc_attempts"] = clamp01(pf.privesc_calls / config.PRIVESC_CAP)
    s["egress_volume"] = zscore_to_unit(pf.egress_bytes, b.egress.mean, b.egress.std)
    if b.iat.n >= 8 and b.iat.variance > 1e-9:
        # bots are too regular: low observed variance vs baseline -> high score
        s["timing_regularity"] = clamp01(1.0 - clamp01(pf.interarrival_var /
                                                       max(b.iat.variance, 1e-9)))
    else:
        s["timing_regularity"] = 0.0        # not enough history to judge rhythm
    return s


def combine_risk(scores: dict) -> float:
    tot = sum(config.AXIS_WEIGHTS.values())
    return sum(config.AXIS_WEIGHTS.get(k, 0.0) * v for k, v in scores.items()) / tot


def risk_level(r: float) -> int:
    if r >= config.RISK_CRITICAL_T:
        return config.CRITICAL
    if r >= config.RISK_ELEVATED_T:
        return config.ELEVATED
    return config.BENIGN


def attractor_shape(scores: dict, b: Baseline) -> Optional[str]:
    """
    Map the anomaly geometry onto the four pathological attractors (spec §10).
    Reuses the unit-level pathology shapes rather than inventing a taxonomy.
    """
    hi = lambda k, t=0.5: scores.get(k, 0.0) >= t          # noqa: E731
    # narcissistic: takes far more than it returns, steady and heavy
    if hi("egress_volume", 0.6) and scores.get("timing_regularity", 0) >= 0.5:
        return "narcissistic"
    # borderline: oscillating probing — spread + cadence, no rhythm
    if hi("endpoint_spread", 0.7) and hi("connection_cadence", 0.5):
        return "borderline"
    # codependent: trust-parasitism — auth anomalies on a host we trust deeply
    if hi("auth_failure_rate", 0.5) and b.n >= 20:
        return "codependent"
    # schizoid: the dangerous one — nothing crosses a threshold, but the rhythm is
    # machine-perfect and the relationship keeps deepening. Temporal, not alerting.
    if b.n >= 50 and scores.get("timing_regularity", 0) >= 0.8 \
            and combine_risk(scores) < config.RISK_ELEVATED_T:
        return "schizoid"
    return None
