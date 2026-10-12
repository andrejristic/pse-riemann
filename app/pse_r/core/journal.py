"""
Append-only journal — the swarm's memory of what actually happened.

Every gate decision, every egress attempt, every theta event, every lab run and
every model call lands here. The table is append-only AT THE DATABASE LEVEL:
SQLite triggers RAISE(ABORT) on UPDATE and DELETE, so a bug (or a compromised
component) cannot quietly rewrite history. That property is the whole point —
the claim ledger's credibility rests on it.

Secrets never reach this file: every payload passes through guardian.secrets.redact
before serialization.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Iterable, Optional

from .. import config

_SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;

CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          REAL    NOT NULL,
    kind        TEXT    NOT NULL,
    actor       TEXT    NOT NULL,
    subject     TEXT,
    verdict     TEXT,
    payload     TEXT    NOT NULL,
    prev_hash   TEXT    NOT NULL,
    hash        TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_kind ON events(kind);
CREATE INDEX IF NOT EXISTS idx_events_ts   ON events(ts);
CREATE INDEX IF NOT EXISTS idx_events_subj ON events(subject);

CREATE TRIGGER IF NOT EXISTS events_no_update
BEFORE UPDATE ON events
BEGIN SELECT RAISE(ABORT, 'journal is append-only: UPDATE forbidden'); END;

CREATE TRIGGER IF NOT EXISTS events_no_delete
BEFORE DELETE ON events
BEGIN SELECT RAISE(ABORT, 'journal is append-only: DELETE forbidden'); END;
"""

# Event kinds (keep the vocabulary small and stable — reports parse these)
GATE = "gate"                 # a write was accepted / rejected by the vault gate
EGRESS = "egress"             # an outbound request was allowed / blocked
THREAT = "threat"             # guardian tier-1 / tier-2 intervention
THETA = "theta"               # theta event (single gate for all theta changes)
LAB = "lab"                   # numerical experiment run
MODEL = "model"               # llm call (provider, role, tokens, cost)
INGEST = "ingest"             # source fetched / promoted / dropped
SYSTEM = "system"             # startup, wizard, config change


class Journal:
    """Thread-safe append-only event log with a per-row hash chain."""

    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path or config.JOURNAL_DB)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    # -- write ------------------------------------------------------------- #
    def append(self, kind: str, actor: str, payload: dict,
               subject: str = "", verdict: str = "") -> int:
        """Append one event. Returns its rowid. Never raises on payload content."""
        from ..guardian.secrets import redact          # local import: avoids a cycle
        safe = redact(payload)
        blob = json.dumps(safe, ensure_ascii=False, sort_keys=True, default=str)
        ts = time.time()
        with self._lock:
            row = self._conn.execute(
                "SELECT hash FROM events ORDER BY id DESC LIMIT 1").fetchone()
            prev = row["hash"] if row else "genesis"
            h = hashlib.sha256(
                f"{prev}|{ts}|{kind}|{actor}|{subject}|{verdict}|{blob}".encode()
            ).hexdigest()
            cur = self._conn.execute(
                "INSERT INTO events (ts,kind,actor,subject,verdict,payload,prev_hash,hash)"
                " VALUES (?,?,?,?,?,?,?,?)",
                (ts, kind, actor, subject, verdict, blob, prev, h))
            self._conn.commit()
            return int(cur.lastrowid)

    # -- read -------------------------------------------------------------- #
    def tail(self, n: int = 50, kind: str = "") -> list[dict]:
        q = "SELECT * FROM events"
        args: list[Any] = []
        if kind:
            q += " WHERE kind=?"
            args.append(kind)
        q += " ORDER BY id DESC LIMIT ?"
        args.append(n)
        with self._lock:
            rows = self._conn.execute(q, args).fetchall()
        return [self._row(r) for r in rows][::-1]

    def since(self, ts: float, kind: str = "") -> list[dict]:
        q = "SELECT * FROM events WHERE ts>=?"
        args: list[Any] = [ts]
        if kind:
            q += " AND kind=?"
            args.append(kind)
        q += " ORDER BY id ASC"
        with self._lock:
            rows = self._conn.execute(q, args).fetchall()
        return [self._row(r) for r in rows]

    def count(self, kind: str = "") -> int:
        with self._lock:
            if kind:
                r = self._conn.execute(
                    "SELECT COUNT(*) c FROM events WHERE kind=?", (kind,)).fetchone()
            else:
                r = self._conn.execute("SELECT COUNT(*) c FROM events").fetchone()
        return int(r["c"])

    @staticmethod
    def _row(r: sqlite3.Row) -> dict:
        d = dict(r)
        try:
            d["payload"] = json.loads(d["payload"])
        except (json.JSONDecodeError, TypeError):
            pass
        return d

    # -- integrity ---------------------------------------------------------- #
    def verify_chain(self) -> tuple[bool, Optional[int]]:
        """
        Recompute the hash chain. Returns (ok, first_bad_id).
        A break means the db file was tampered with out-of-process — the triggers
        stop in-process rewrites, this catches everything else.
        """
        prev = "genesis"
        with self._lock:
            rows = self._conn.execute("SELECT * FROM events ORDER BY id ASC").fetchall()
        for r in rows:
            h = hashlib.sha256(
                f"{prev}|{r['ts']}|{r['kind']}|{r['actor']}|{r['subject']}|"
                f"{r['verdict']}|{r['payload']}".encode()).hexdigest()
            if h != r["hash"] or r["prev_hash"] != prev:
                return False, int(r["id"])
            prev = r["hash"]
        return True, None

    def close(self) -> None:
        with self._lock:
            self._conn.close()


_JOURNAL: Optional[Journal] = None


def journal() -> Journal:
    """Process-wide singleton. Everything logs through this."""
    global _JOURNAL
    if _JOURNAL is None:
        _JOURNAL = Journal()
    return _JOURNAL


def log(kind: str, actor: str, payload: dict, subject: str = "", verdict: str = "") -> int:
    return journal().append(kind, actor, payload, subject, verdict)
