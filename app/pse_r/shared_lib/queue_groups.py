"""
"Čeka tvoju odluku" in groups (plan 33d; agreement rule 32).

A tree: kind of item → group (the mission for mission items, the corpus branch
for papers — taken deterministically from title + abstract) → items. The
operator ticks one, several or all items (or a whole group) and decides them
together — but only items whose decision can be undone may be decided in bulk.
A Doctor's measure and every irreversible item are decided one by one.
"""
from __future__ import annotations

from typing import Optional

from .store import store

KIND_LABEL = {
    "doctor-measure": "Doktorove mjere",
    "pse-undo": "Poništavanje fisije/fuzije",
    "vote-weights": "Težine glasova",
    "arxiv-paper": "Novi radovi (arXiv)",
    "mission-proposal": "Prijedlozi iz razgovora o misiji",
    "mission-goal": "Cilj misije",
    "mission-switch": "Promjena aktivne misije",
    "skeptic": "Prigovori skeptika",
    "adversary": "Adversarijalni nalazi",
    "method": "Metode (prošle vrata)",
    "paper-draft": "Radni tekst",
    "declarations": "Deklaracije",
    "quarantine": "Karantin hosta",
    "guard-pause": "„→ ∞“: pauza poziva modelu",
    "online-ai-closed": "Online AI isključen",
    "integrity": "Integritet dnevnika",
    "archive": "Arhiva dnevnika",
    "ssh-permanent": "SSH: trajna blokada",
    "ssh-stop": "SSH: zaustavljanje servera",
}

# Decisions that can be undone (or only add something the operator can remove
# later): these may be decided in bulk. Everything else — and every kind not
# listed — is one by one [rule 32].
BULK_OK = {"arxiv-paper", "mission-proposal", "skeptic", "adversary", "paper-draft",
           "mission-switch", "mission-goal"}
ONE_BY_ONE_REASON = "Doktorova mjera ili nepovratna odluka — samo jedna po jedna"


def bulk_allowed(item: dict) -> bool:
    return item.get("kind") in BULK_OK


def _mission_title(mid: str) -> str:
    from . import missions as MIS
    m = MIS.get(mid) if mid else None
    return m["title"] if m else (mid or "")


def _topic(item: dict) -> str:
    from ..ingest import topics as T
    p = item.get("payload") or {}
    text = f"{p.get('title') or item.get('title', '')} {p.get('abstract') or ''}"
    key, score = T.best_branch(text)
    if not key or score <= 0:
        return "ostalo"
    b = T.BY_KEY.get(key)
    return b.title if b else key


def subgroup(item: dict) -> str:
    p = item.get("payload") or {}
    kind = item.get("kind", "")
    if kind == "arxiv-paper":
        return _topic(item)
    mid = p.get("mission") or p.get("mission_id")
    if mid:
        return _mission_title(mid)
    if kind == "doctor-measure":
        return p.get("agent") or p.get("unit", "")
    return ""


def tree(items: Optional[list] = None) -> list[dict]:
    """[{kind, label, bulk, groups: [{name, items: [...]}]}], sorted by kind label."""
    items = store().open_items() if items is None else items
    kinds: dict = {}
    for it in items:
        k = it.get("kind", "?")
        kinds.setdefault(k, {}).setdefault(subgroup(it), []).append(it)
    out = []
    for k, groups in kinds.items():
        out.append({"kind": k, "label": KIND_LABEL.get(k, k), "bulk": k in BULK_OK,
                    "groups": [{"name": g, "items": groups[g]} for g in sorted(groups)]})
    order = list(KIND_LABEL)
    out.sort(key=lambda d: (order.index(d["kind"]) if d["kind"] in order else 99, d["label"]))
    return out


def decide_many(ids: list, approve: bool, reason: str = "") -> dict:
    """Decide several items; refuses (does nothing) if any of them may not be
    decided in bulk. Returns {"done": [...], "failed": {id: error}}."""
    items = [store().get(i) for i in ids]
    if len(ids) > 1:
        bad = [i["id"] for i in items if i and not bulk_allowed(i)]
        if bad:
            raise ValueError(f"{ONE_BY_ONE_REASON}: {', '.join(bad)}")
    done, failed = [], {}
    for i in ids:
        try:
            store().decide(i, approve, reason or ("grupna odluka" if len(ids) > 1 else ""))
            done.append(i)
        except Exception as e:                          # noqa: BLE001 — reported per item
            failed[i] = str(e)[:200]
    return {"done": done, "failed": failed}


def detail_md(item: dict) -> str:
    """Everything about one item (the full abstract included)."""
    p = item.get("payload") or {}
    L = [f"### {item['title']}", "",
         f"**{KIND_LABEL.get(item['kind'], item['kind'])}** · predložio: {item.get('proposer', '')}"
         + ("" if bulk_allowed(item) else f" · _{ONE_BY_ONE_REASON}_"), ""]
    if p.get("abstract"):
        L += ["**Sažetak:**", "", p["abstract"], ""]
    if p.get("ref"):
        L.append(f"**Izvor:** `{p['ref']}`")
    if item["kind"] == "doctor-measure":
        f = p.get("finding") or {}
        L += [f"**Jedinica:** {p.get('unit')} · **mjera:** {p.get('measure')}",
              f"**Zašto:** {f.get('why', '')}",
              "**Okidači:** " + ", ".join(p.get("labels_sr") or f.get("triggers") or [])]
    res = p.get("result") or {}
    if res.get("computed_B") is not None:
        L.append(f"**Reprodukcija:** naš B*={res['computed_B']:.12f}, rad {res.get('claimed_B')}, "
                 f"razlika {res.get('error', 0):.1e}")
    for k in ("text", "reason", "summary", "command", "path"):
        if p.get(k):
            L.append(f"**{k}:** {str(p[k])[:2000]}")
    return "\n\n".join(x for x in L if x is not None)
