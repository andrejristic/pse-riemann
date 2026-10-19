"""
Full-text search over the vault and the inbox — SQLite FTS5, BM25 ranked.

The index is a derived accelerator, never the source of truth: it can be
deleted and rebuilt from the markdown at any time, and `reindex()` is cheap
enough (a few thousand cards is well under a second on this machine) that the
app just does it at startup.

FTS5 rather than embeddings, deliberately. Embeddings would mean a model file,
a torch or onnx runtime, and several hundred megabytes of RAM that this laptop
does not have to spare. For a corpus of your own notes, where you remember
roughly what you wrote, BM25 over exact terms is not a compromise — for
"Gramov zakon" or "Guth-Maynard" it is better.
"""
from __future__ import annotations

import json
import re
import sqlite3
import threading
from pathlib import Path
from typing import Optional

from .. import config
from . import store as VS

_SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE VIRTUAL TABLE IF NOT EXISTS cards USING fts5(
    id UNINDEXED, kind UNINDEXED, status UNINDEXED, path UNINDEXED,
    title, body, tags,
    tokenize='unicode61 remove_diacritics 2'
);
CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT);
"""


class Index:
    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path or config.INDEX_DB)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    # ------------------------------------------------------------------ #
    def reindex(self) -> dict:
        n_cards = n_inbox = 0
        with self._lock:
            self._conn.execute("DELETE FROM cards")
            for c in VS.iter_cards():
                p = VS.path_of(c.id)
                self._conn.execute(
                    "INSERT INTO cards (id,kind,status,path,title,body,tags)"
                    " VALUES (?,?,?,?,?,?,?)",
                    (c.id, c.type, c.status, str(p) if p else "",
                     c.title, c.body, " ".join(c.tags)))
                n_cards += 1
            for f in sorted(config.DIR_INBOX.glob("*.json")):
                try:
                    d = json.loads(f.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    continue
                if d.get("_state") == "dropped":
                    continue
                self._conn.execute(
                    "INSERT INTO cards (id,kind,status,path,title,body,tags)"
                    " VALUES (?,?,?,?,?,?,?)",
                    (d.get("source_ref", f.stem), "inbox",
                     d.get("_state", "new"), str(f),
                     d.get("title", ""), d.get("abstract", ""),
                     d.get("_branch", "")))
                n_inbox += 1
            self._conn.commit()
        return {"cards": n_cards, "inbox": n_inbox}

    # ------------------------------------------------------------------ #
    def search(self, q: str, limit: int = 30, kind: str = "") -> list[dict]:
        query = _to_fts(q)
        if not query:
            return []
        sql = ("SELECT id,kind,status,path,title,"
               "snippet(cards, 5, '«', '»', ' … ', 14) AS snip,"
               "bm25(cards, 0,0,0,0, 6.0, 1.0, 3.0) AS rank "
               "FROM cards WHERE cards MATCH ?")
        args: list = [query]
        if kind:
            sql += " AND kind = ?"
            args.append(kind)
        sql += " ORDER BY rank LIMIT ?"
        args.append(limit)
        with self._lock:
            try:
                rows = self._conn.execute(sql, args).fetchall()
            except sqlite3.OperationalError:
                # a malformed FTS expression: fall back to a plain phrase
                rows = self._conn.execute(
                    sql.replace("cards MATCH ?", "cards MATCH ?"),
                    ['"' + q.replace('"', " ") + '"'] + args[1:]).fetchall()
        return [dict(r) for r in rows]

    def close(self) -> None:
        with self._lock:
            self._conn.close()


_TOKEN = re.compile(r"[^\w\-]+", re.UNICODE)


def _to_fts(q: str) -> str:
    """
    Turn a human query into a safe FTS5 expression. Users type "Gramov zakon",
    not `"gramov" AND "zakon"`, and they should never see a syntax error from
    an apostrophe.
    """
    q = (q or "").strip()
    if not q:
        return ""
    if q.startswith('"') and q.endswith('"') and len(q) > 2:
        return q
    parts = [p for p in _TOKEN.split(q) if p]
    if not parts:
        return ""
    return " ".join(f'"{p}"*' if len(p) > 3 else f'"{p}"' for p in parts)


_IDX: Optional[Index] = None


def index() -> Index:
    global _IDX
    if _IDX is None:
        _IDX = Index()
    return _IDX


def search(q: str, limit: int = 30, kind: str = "") -> list[dict]:
    return index().search(q, limit, kind)
