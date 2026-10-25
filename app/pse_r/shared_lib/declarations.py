"""
Declarations (master §0.5.5): facts a guard cannot work out for itself.

The system PROPOSES them; a human CONFIRMS them once; from then on they are
fixed inputs and everything built on them is deterministic. A proposal never
takes effect by itself. Every confirmed set is a new, numbered version, kept
forever and signed with the operator's name.

What PSE Riemann declares:
  models          weights hash (sha256) of every GGUF the app may load, by path
  sources         hosts the ingest side may read (mirrors guardian.policy)
  destinations    where a final report may be written / exported
  protected       objects that must never leave (secrets file, TLS pins, host ids)
  languages       languages the operator writes in (letter tables, §10.3)
"""
from __future__ import annotations

import json
import time
from typing import Optional

from ..core import journal as J
from . import operator as OP
from .store import store

KINDS = ("models", "sources", "destinations", "protected", "languages")
PROPOSAL_KIND = "declarations"


def current() -> dict:
    r = store().rows("SELECT * FROM declarations ORDER BY version DESC LIMIT 1")
    if not r:
        return {"version": 0, **{k: {} if k == "models" else [] for k in KINDS}}
    d = json.loads(r[0]["data"])
    d["version"] = r[0]["version"]
    d["confirmed_by"] = r[0]["confirmed_by"]
    return d


def default_proposal() -> dict:
    """What the system proposes from what it already knows."""
    from .. import config
    from ..guardian import policy
    return {
        "models": {},
        "sources": sorted({h["host"] for h in policy.describe()
                           if h.get("host")}),
        "destinations": [str(config.DIR_REPORTS)],
        "protected": [str(config.SECRETS_FILE), str(config.PIN_STORE)],
        "languages": ["sr-Latn", "en"],
    }


def propose(changes: dict, proposer: str) -> str:
    """Queue a change for the human. Nothing takes effect here."""
    bad = set(changes) - set(KINDS)
    if bad:
        raise ValueError(f"nepoznate vrste deklaracija: {sorted(bad)}")
    return store().propose(PROPOSAL_KIND, "Deklaracije: " + ", ".join(sorted(changes)),
                           {"changes": changes}, proposer)


def confirm(changes: dict) -> int:
    """Apply a confirmed change set. Only reachable through a human decision."""
    who = OP.require_operator()
    cur = current()
    new = {k: cur.get(k, {} if k == "models" else []) for k in KINDS}
    for k, v in changes.items():
        if k == "models":
            new["models"] = {**new["models"], **v}
        else:
            new[k] = list(v)
    ver = int(cur.get("version", 0)) + 1
    store().execute("INSERT INTO declarations(version,data,confirmed_by,confirmed_at)"
                    " VALUES (?,?,?,?)",
                    (ver, json.dumps(new, ensure_ascii=False, sort_keys=True), who,
                     time.time()))
    J.log(J.SYSTEM, who, {"event": "declarations_confirmed", "version": ver,
                          "kinds": sorted(changes)}, verdict="confirmed")
    return ver


def _on_decision(item: dict, approved: bool) -> None:
    if approved:
        confirm(item["payload"]["changes"])


def model_hash(path: str) -> Optional[str]:
    return current().get("models", {}).get(path)


def install_hooks() -> None:
    store().on_decision(PROPOSAL_KIND, _on_decision)
