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

# Round 3, items 26–27: every mission has a GOAL the operator chooses (always in the
# Missions menu). The app may only PROPOSE a change (human queue), never make it.
GOALS = {1: "mapa prenosivosti (podrazumijevano)", 2: "E_d i T_d uslovno (pod pretpostavkom)",
         3: "samo praćenje (kartice i ideje)"}
GOAL_KIND = "mission-goal"
SECOND_ID = "misija-visi-stepen"


def _migrate() -> None:
    cols = {r["name"] for r in store().rows("PRAGMA table_info(missions)")}
    if "goal" not in cols:
        store().execute("ALTER TABLE missions ADD COLUMN goal INTEGER NOT NULL DEFAULT 1")

FIRST_ID = "misija-kontinualna-transformacija"
TARGETS = (0.87, 5 / 6, 3 / 4, 1 / 2)


def _ensure() -> None:
    store().ensure(_SCHEMA)
    _migrate()


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
    front = B if old is None else min(old, B)
    nearest = min(TARGETS, key=lambda t: abs(t - front))
    new_state = (f"Front na B={front:.9f}. Zadnji unos ({method_name}) "
                 f"{'je prva tačka' if old is None else f'je {outcome} (prije {old:.9f})'}; "
                 f"najbliži cilj {nearest:.6f}, udaljenost {abs(front - nearest):.6f}.")
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


# --------------------------------------------------------------------------- #
# goals (round 3, items 26–27)
# --------------------------------------------------------------------------- #
def set_goal(mid: str, goal: int, reason: str = "") -> None:
    """Only the operator changes a mission's goal; journalled with the name."""
    _ensure()
    who = OP.require_operator()
    if goal not in GOALS:
        raise ValueError(f"cilj mora biti 1, 2 ili 3 (ne {goal})")
    m = get(mid)
    if m is None:
        raise KeyError(mid)
    store().execute("UPDATE missions SET goal=?, updated=? WHERE id=?", (goal, time.time(), mid))
    J.log(J.MISSION, who, {"event": "goal_changed", "id": mid, "from": m.get("goal", 1),
                           "to": goal, "reason": reason[:300]}, subject=mid, verdict="goal")


def propose_goal(mid: str, goal: int, why: str, proposer: str = "system") -> str:
    """The app's only way to change a goal: ask the operator."""
    if goal not in GOALS:
        raise ValueError("cilj mora biti 1, 2 ili 3")
    for it in store().open_items(GOAL_KIND):
        if it["payload"].get("mission") == mid and it["payload"].get("goal") == goal:
            return it["id"]
    return store().propose(GOAL_KIND, f"Prijedlog: cilj misije „{mid}“ → {goal} ({GOALS[goal]})",
                           {"mission": mid, "goal": goal, "why": why[:1000]}, proposer)


def _on_goal_decision(item: dict, approved: bool) -> None:
    if approved:
        set_goal(item["payload"]["mission"], int(item["payload"]["goal"]),
                 "odobren prijedlog: " + item["payload"].get("why", "")[:200])


def install_hooks() -> None:
    store().on_decision(GOAL_KIND, _on_goal_decision)


# The transfer map of mission 2 (goal 1): every step of the 7/8 proof and whether
# it carries over to higher degree. First draft from research/langlands-2026-10
# (§4) — our reading, unreviewed; each later decision is a mission step.
TRANSFER_MAP = [
    ("Möbiusove sume nad karakterima", "vjerovatno se prenosi (koeficijenti 1/L)",
     "izvor-large-sieve-gln-2508-14888"),
    ("Gaussove sume → kubna theta (Kubota/Patterson)", "nema poznatog analoga — glavna prepreka",
     "tema-visi-stepen"),
    ("kvadratni large sieve", "GL_n large sieve postoji — prenosi se uz gubitak (utiče na eksponent)",
     "izvor-large-sieve-gln-2508-14888"),
    ("funkcionalna jednačina / analitičko produženje",
     "Sym^n: Newton–Thorne (recenzirano); Artin: pretpostavka", "izvor-newton-thorne-i"),
]


def seed_second() -> str:
    """Mission 2 (round 3, item 27). Idempotent."""
    _ensure()
    if get(SECOND_ID) is not None:
        return SECOND_ID
    create(SECOND_ID, "Viši stepen: prenosi li se 7/8?",
           "Prenosi li se metoda 7/8 (Liu, Xu–Sang) na L-funkcije višeg stepena (GL(2), Artin)? "
           "Ako da, kako se eksponent mijenja sa stepenom d i postoji li T_d između porodica? "
           "Vrsta rezultata: poluravan bez nula (ne miješati sa udjelom na pravoj).",
           state="Otvoreno pitanje. Prvi nacrt mape prenosivosti (NAŠE-NERECENZIRANO): "
                 "glavna prepreka je korak Gaussove sume → kubna theta.")
    for step_name, verdict, ref in TRANSFER_MAP:
        step(SECOND_ID, f"korak dokaza: {step_name}", verdict,
             "mapa prenosivosti u izradi (cilj 1)", ref=ref)
    return SECOND_ID
