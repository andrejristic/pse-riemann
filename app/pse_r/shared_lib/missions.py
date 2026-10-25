"""
Missions (plan F9, PSE-L level L3: state → action → outcome).

A mission is a standing question the system is working on. It is not a to-do
list: it is a living record of where the frontier is and which way the last
piece of evidence moved it. Each mission carries the lowest exponent B it has
seen (the frontier) and a log of steps, each a {state, action, outcome} triple
in the PSE-L sense:

    state     where the frontier stood before this step
    action    what happened (a method imported, an extension explored)
    outcome   which way it moved — bliže / dalje / zid — and the new frontier

Missions live in the SHARED_LIB store, so `missions` and `mission_steps` are
automatically part of the read-only fact layer (views.py attaches every store
table). The first mission is the one the author dictated: is there a continuous
transformation between QRH methods, and does extending it move B toward the
targets (0.87, 5/6, 3/4, 1/2) or away?
"""
from __future__ import annotations

import time
from typing import Optional

from ..core import journal as J
from . import operator as OP
from .store import store

_SCHEMA = [
    """CREATE TABLE IF NOT EXISTS missions (
        id       TEXT PRIMARY KEY,
        title    TEXT NOT NULL,
        question TEXT NOT NULL,
        state    TEXT NOT NULL,
        best_B   REAL,
        created  REAL NOT NULL,
        updated  REAL NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS mission_steps (
        id         INTEGER PRIMARY KEY,
        mission_id TEXT NOT NULL,
        ts         REAL NOT NULL,
        state      TEXT NOT NULL,
        action     TEXT NOT NULL,
        outcome    TEXT NOT NULL,
        ref        TEXT
    )""",
    "CREATE INDEX IF NOT EXISTS idx_steps_mission ON mission_steps(mission_id)",
]

FIRST_ID = "misija-kontinualna-transformacija"
TARGETS = (0.87, 5 / 6, 3 / 4, 1 / 2)


def _ensure() -> None:
    store().ensure(_SCHEMA)


def create(mid: str, title: str, question: str, state: str,
           best_B: Optional[float] = None) -> str:
    _ensure()
    now = time.time()
    store().execute(
        "INSERT OR IGNORE INTO missions(id,title,question,state,best_B,created,updated)"
        " VALUES (?,?,?,?,?,?,?)", (mid, title, question, state, best_B, now, now))
    J.log(J.MISSION, OP.current() or "system",
          {"event": "created", "id": mid, "title": title, "best_B": best_B},
          subject=mid, verdict="open")
    return mid


def get(mid: str) -> Optional[dict]:
    _ensure()
    r = store().rows("SELECT * FROM missions WHERE id=?", (mid,))
    if not r:
        return None
    m = r[0]
    m["steps"] = store().rows(
        "SELECT ts,state,action,outcome,ref FROM mission_steps WHERE mission_id=? "
        "ORDER BY ts", (mid,))
    return m


def all_missions() -> list[dict]:
    _ensure()
    return store().rows("SELECT * FROM missions ORDER BY created")


def step(mid: str, action: str, outcome: str, new_state: str,
         best_B: Optional[float] = None, ref: str = "") -> None:
    """Record one {state, action, outcome} step and move the mission forward."""
    _ensure()
    m = get(mid)
    if m is None:
        raise KeyError(mid)
    prev_state = m["state"]
    now = time.time()
    store().execute(
        "INSERT INTO mission_steps(mission_id,ts,state,action,outcome,ref)"
        " VALUES (?,?,?,?,?,?)", (mid, now, prev_state, action, outcome, ref))
    best = m["best_B"]
    if best_B is not None and (best is None or best_B < best):
        best = best_B
    store().execute("UPDATE missions SET state=?, best_B=?, updated=? WHERE id=?",
                    (new_state, best, now, mid))
    J.log(J.MISSION, OP.current() or "system",
          {"event": "step", "id": mid, "action": action, "outcome": outcome,
           "best_B": best}, subject=mid, verdict=outcome)


def record_method(mid: str, method_name: str, B: float, source: str = "") -> str:
    """
    A method was accepted against this mission. Compare its boundary to the
    current frontier and record the outcome (bliže / dalje / isto), noting how
    far it still is from the nearest target.
    """
    from ..methods import core as C
    m = get(mid)
    if m is None:
        raise KeyError(mid)
    old = m["best_B"]
    outcome = "bliže" if old is None else C.verdict(old, B)
    nearest = min(TARGETS, key=lambda t: abs(t - B))
    new_state = (f"Front na B={B:.9f}. Zadnji unos ({method_name}) "
                 f"{'je prva tačka' if old is None else f'je {outcome} (prije {old:.9f})'}; "
                 f"najbliži cilj {nearest:.6f}, udaljenost {abs(B - nearest):.6f}.")
    action = f"uvezena i potvrđena metoda {method_name} (B*={B:.9f})"
    outcome_line = (f"{outcome}: front {old:.9f} → {B:.9f}" if old is not None
                    else f"prva tačka fronta: {B:.9f}")
    step(mid, action, outcome_line, new_state, best_B=B, ref=source or method_name)
    return outcome


def seed_first() -> str:
    """The mission the author dictated (REPORT §7). Idempotent."""
    _ensure()
    if get(FIRST_ID) is not None:
        return FIRST_ID
    return create(
        FIRST_ID,
        "Kontinualna transformacija između QRH metoda",
        "Postoji li kontinualna funkcija transformacije koja eksponent visoke "
        "strane jedne QRH metode prevodi u sljedeću (Liu → Xu–Sang: "
        "E_XS = E_Liu + T, potvrđeno), i da li njeno proširenje (t, w, nove "
        "familije) pomjera B prema ciljevima (0.87, 5/6, 3/4, 1/2) ili od njih? "
        "Svaki novi rad = nova tačka i nova T.",
        state=("Otvorena. Unutar Liu/Xu–Sang familije transformacija JESTE "
               "kontinualna; proširenja se približavaju do zidova (~0.870 / 5/6), "
               "ne prema 1/2. Svaki novi rad kroz vrata dodaje tačku."),
        best_B=None)
