"""
Replayable decisions (round 3, item 6; Perun P1).

The journal's hash chain proves that a record was not CHANGED. It does not
prove that the decision it records was RIGHT. For that, every automatic
decision that matters is written together with what it was decided from:

    {"replay": {"decider": "gate.decide", "v": 1,
                "in": {...}, "in_sha": "<sha256 of the inputs>", "out": {...}}}

Later, replay_all() re-runs each decider on its recorded inputs and compares
the result with the recorded output. A disagreement means either the record
or the decider was tampered with — an INTEGRITY VIOLATION: it is journalled as
a threat and put in front of the operator.

Honest limits, reported rather than hidden:
  * "redigovano"   the journal redacts secrets before writing; if that changed
                   the inputs, their sha no longer matches and the record cannot
                   be replayed (counted, never called a violation);
  * "druga verzija" the decider changed since (another `v`); not comparable;
  * "nepoznat"     no decider by that name in this build.

Deciders are pure functions of JSON data: no clock, no file system, no model.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Callable, Optional

from . import journal as J

INTEGRITY_KIND = "integrity"            # human-queue item on a mismatch


class NotComparable(Exception):
    """The decider's world changed legitimately (e.g. a new allowlist): the
    record is not comparable with this build — counted as another version."""


def canon(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str,
                      separators=(",", ":"))


def sha(obj) -> str:
    return hashlib.sha256(canon(obj).encode("utf-8")).hexdigest()


@dataclass
class Decider:
    name: str
    v: int
    fn: Callable[[dict], dict]


_DECIDERS: dict[str, Decider] = {}


def decider(name: str, v: int = 1):
    """Register a pure decider: fn(inputs: dict) -> output: dict (JSON data)."""
    def wrap(fn):
        _DECIDERS[name] = Decider(name, v, fn)
        return fn
    return wrap


def record(name: str, inputs: dict, output: dict) -> dict:
    """The block to put under payload["replay"]. Normalised through JSON so the
    recorded output is exactly what a replay will produce."""
    _load_deciders()
    d = _DECIDERS.get(name)
    inputs = json.loads(canon(inputs))
    output = json.loads(canon(output))
    return {"decider": name, "v": d.v if d else 0, "in": inputs,
            "in_sha": sha(inputs), "out": output}


def decide(name: str, inputs: dict) -> tuple[dict, dict]:
    """Run a registered decider and return (output, replay-record)."""
    _load_deciders()
    out = _DECIDERS[name].fn(json.loads(canon(inputs)))
    return out, record(name, inputs, out)


@dataclass
class Report:
    checked: int = 0
    ok: int = 0
    mismatches: list = field(default_factory=list)      # [(event id, decider)]
    redacted: int = 0
    other_version: int = 0
    unknown: int = 0
    errors: list = field(default_factory=list)

    @property
    def intact(self) -> bool:
        return not self.mismatches

    def summary(self) -> str:
        s = (f"{self.ok}/{self.checked} odluka ponovljeno istovjetno")
        extra = []
        if self.mismatches:
            extra.append(f"⛔ {len(self.mismatches)} NESLAGANJE")
        if self.redacted:
            extra.append(f"{self.redacted} redigovano")
        if self.other_version:
            extra.append(f"{self.other_version} druga verzija")
        if self.unknown:
            extra.append(f"{self.unknown} nepoznat odlučivač")
        return s + (" · " + ", ".join(extra) if extra else "")


def replay_event(ev: dict) -> str:
    """'ok' | 'mismatch' | 'redacted' | 'other_version' | 'unknown' | 'error'."""
    r = (ev.get("payload") or {}).get("replay")
    if not r:
        return ""
    d = _DECIDERS.get(r.get("decider", ""))
    if d is None:
        return "unknown"
    if r.get("v") != d.v:
        return "other_version"
    if sha(r.get("in")) != r.get("in_sha"):
        return "redacted"
    try:
        out = json.loads(canon(d.fn(r["in"])))
    except NotComparable:
        return "other_version"
    except Exception:                                   # noqa: BLE001
        return "error"
    return "ok" if canon(out) == canon(r.get("out")) else "mismatch"


def replay_all(events: Optional[list] = None, notify: bool = True) -> Report:
    """Re-derive every recorded decision. Mismatches → threat + operator."""
    _load_deciders()
    rep = Report()
    for ev in (events if events is not None else J.journal().with_replay()):
        st = replay_event(ev)
        if not st:
            continue
        rep.checked += 1
        if st == "ok":
            rep.ok += 1
        elif st == "mismatch":
            rep.mismatches.append((ev.get("id"), ev["payload"]["replay"]["decider"]))
        elif st == "redacted":
            rep.redacted += 1
        elif st == "other_version":
            rep.other_version += 1
        elif st == "unknown":
            rep.unknown += 1
        else:
            rep.errors.append(ev.get("id"))
    if rep.mismatches and notify:
        J.log(J.THREAT, "replay", {"event": "integrity_violation",
                                   "mismatches": rep.mismatches[:50]},
              subject="journal", verdict="threat")
        from ..shared_lib.store import store
        if not store().open_items(INTEGRITY_KIND):
            ids = ", ".join(str(i) for i, _ in rep.mismatches[:10])
            store().propose(INTEGRITY_KIND,
                            f"NARUŠEN INTEGRITET: {len(rep.mismatches)} odluka se ne može "
                            f"ponovo izvesti iz dnevnika (zapisi {ids}). Provjeri.",
                            {"mismatches": rep.mismatches[:200]}, proposer="replay")
    return rep


def _load_deciders() -> None:
    """Import the modules that register deciders (they register on import)."""
    from . import replay_deciders     # noqa: F401
