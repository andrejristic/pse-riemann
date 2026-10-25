"""
SHARED_LIB at runtime — the heartbeat that makes the library an overseer while
the app is open (wired 2026-10-25 after review: these pieces existed as library
code and tests but nothing ran them).

tick()            called by the GUI timer (and `main.py --tick`):
  * KEEPERS       every file in vault/reports is sealed when it appears; keeper
                  units are allocated in proportion to resources (not 1:1) and
                  patrol the seals; a broken seal is restored, logged as a threat,
                  and the physician opens a case for the file harm
  * ARXIV         at most once a day and only if the network answers: new QRH
                  papers become queue items "izvući metodu?" — the operator decides
                  whether the main AI may spend effort extracting it

check_output()    every model output the app shows is screened for the three
                  harms; any finding = infection → contain, diagnose, treat
                  (tier-2 steps go to the human queue) and the agent stays
                  contained until the operator releases it

write_final_report() puts a final report under vault/reports and seals it.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from .. import config
from ..core import journal as J
from . import operator as OP
from . import reports as RP
from .store import store

REPORT_EXT = {".md", ".txt", ".pdf", ".html", ".json", ".png"}
ARXIV_INTERVAL_S = 24 * 3600
ARXIV_KIND = "arxiv-paper"
RELEASE_KIND = "heal-release"

_contained: dict[str, str] = {}          # agent -> case signature
_SYNC_FOR_TESTS = False


# --------------------------------------------------------------------------- #
# keepers
# --------------------------------------------------------------------------- #
def _report_files() -> list[Path]:
    d = config.DIR_REPORTS
    if not d.exists():
        return []
    return sorted(p for p in d.rglob("*") if p.is_file() and p.suffix.lower() in REPORT_EXT)


def keepers_round() -> dict:
    """Seal what is new, allocate keepers, patrol. Returns a summary."""
    files = _report_files()
    sealed_paths = {r["path"] for r in RP.sealed()}
    newly = []
    for p in files:
        if str(p.resolve()) not in sealed_paths:
            RP.seal(p, actor="keeper")
            newly.append(p.name)
    n = len(files)
    keepers = RP.keepers_for(n)
    prev = store().kv_get("keepers_allocated", 0)
    if keepers != prev:
        J.log(J.UNIT, "shared_lib", {"event": "keepers_allocated", "keepers": keepers,
                                     "reports": n, "previous": prev},
              subject="keepers", verdict="allocated")
        store().kv_set("keepers_allocated", keepers)
    events = RP.patrol(actor="keeper") if keepers else []
    for ev in events:
        from ..guardian import harms as HRM
        rec = next((r for r in RP.sealed() if r["path"] == ev["path"]), None)
        findings = HRM.to_file(ev["path"], via_gate=False,
                               expected_hash=(rec or {}).get("sha256", "x"),
                               actual_hash="", sealed=True)
        _infect(f"nepoznat-pisac:{Path(ev['path']).name}", findings, release=False)
    return {"reports": n, "keepers": keepers, "sealed_now": newly,
            "tampered": [e["path"] for e in events]}


def write_final_report(name: str, text: str, actor: Optional[str] = None) -> Path:
    """Write a final report and seal it at once (the keepers take it from here)."""
    from ..guardian import content as C
    d = config.DIR_REPORTS
    d.mkdir(parents=True, exist_ok=True)
    fname = C.safe_filename(name)
    if not fname.endswith(".md"):
        fname += ".md"
    p = d / fname
    if p.exists():
        p = d / f"{p.stem}-{time.strftime('%H%M%S')}{p.suffix}"
    p.write_text(text, encoding="utf-8")
    J.log(J.REPORT, actor or OP.current() or "system",
          {"event": "issued", "path": str(p)}, subject=p.name, verdict="issued")
    RP.seal(p, actor=actor)
    return p


# --------------------------------------------------------------------------- #
# the three harms → healing
# --------------------------------------------------------------------------- #
def _infect(agent: str, findings: list, release: bool = True):
    if not findings:
        return None
    from ..guardian.healing import healer
    h = healer()
    case = h.detect(agent, findings)
    h.diagnose(case)
    h.treat(case)
    _contained[agent] = case.signature
    if release:
        store().propose(RELEASE_KIND, f"Pusti agenta [{agent}] iz karantina (oporavak)",
                        {"agent": agent, "harms": [f.sign for f in findings],
                         "evidence": [f.evidence[:200] for f in findings]},
                        proposer="physician")
    return case


def _on_release(item: dict, approved: bool) -> None:
    agent = item["payload"]["agent"]
    if not approved:
        return
    from ..guardian.healing import healer
    case = healer().cases.get(agent)
    if case is not None:
        healer().recover(case)
        healer().immunize(case)
    _contained.pop(agent, None)


def is_contained(agent: str) -> bool:
    return agent in _contained


def check_output(agent: str, text: str, *, sources: Optional[list] = None,
                 data_in_context: str = "", final: bool = False) -> list:
    """
    Screen one model output. Chat replies are checked for the agent harms
    (injection carried in from data, uncritical "sir yes sir" agreement, proof
    claims); FINAL outputs (reports, voice answers) also for harms to the human
    (numbers without a source, preprint as fact, private data).
    """
    from ..guardian import harms as HRM
    findings = HRM.to_agent(text_from_data=data_in_context, reply=text)
    if final:
        findings += HRM.to_human(text, sources=sources or [])
    else:
        from ..vault.gate import _claims_proof
        claims, sentence = _claims_proof(text or "")
        if claims:
            findings.append(HRM.Finding(HRM.HUMAN, "tvrdnja-o-dokazu", sentence[:200],
                                        HRM.HIGH))
    if findings:
        _infect(agent, findings)
    return findings


# --------------------------------------------------------------------------- #
# arXiv
# --------------------------------------------------------------------------- #
def arxiv_round(force: bool = False, fetch=None) -> dict:
    """At most daily: new QRH papers → queue items asking whether to extract."""
    last = store().kv_get("arxiv_last", 0)
    if not force and time.time() - last < ARXIV_INTERVAL_S:
        return {"skipped": True}
    from ..methods import arxiv as AX
    items = (fetch or AX.watch)()
    store().kv_set("arxiv_last", time.time())
    seen = set(store().kv_get("arxiv_seen", []))
    new = []
    for it in items:
        rid = getattr(it, "source_ref", "") or getattr(it, "id", "") or getattr(it, "url", "")
        if not rid or rid in seen:
            continue
        seen.add(rid)
        title = getattr(it, "title", rid)
        store().propose(ARXIV_KIND, f"Novi QRH rad: {title[:120]} — izvući metodu?",
                        {"ref": rid, "title": title,
                         "abstract": (getattr(it, "abstract", "") or "")[:2000]},
                        proposer="arxiv")
        new.append(rid)
    store().kv_set("arxiv_seen", sorted(seen))
    J.log(J.INGEST, "arxiv", {"event": "qrh_watch", "found": len(items), "new": new},
          verdict="watched")
    return {"skipped": False, "found": len(items), "new": new}


def _on_arxiv(item: dict, approved: bool) -> None:
    """Approved → the main AI extracts a method pack, which goes through the door."""
    if not approved:
        return
    import threading

    def work():
        from ..methods import extract as EXT
        try:
            EXT.extract_and_propose(item["payload"]["ref"], item["payload"].get("title", ""))
        except Exception as e:                          # noqa: BLE001
            J.log(J.METHOD, "extract", {"event": "failed", "ref": item["payload"]["ref"],
                                        "error": str(e)[:300]}, verdict="failed")
    # a model call takes minutes: never block the window; the result lands in
    # the queue (reproduced) or in the journal (failed / refused at the door)
    t = threading.Thread(target=work, name="extract", daemon=True)
    t.start()
    if _SYNC_FOR_TESTS:
        t.join()


# --------------------------------------------------------------------------- #
def install_hooks() -> None:
    store().on_decision(RELEASE_KIND, _on_release)
    store().on_decision(ARXIV_KIND, _on_arxiv)


def tick(online: Optional[bool] = None) -> dict:
    out = {"keepers": keepers_round()}
    if online:
        try:
            out["arxiv"] = arxiv_round()
        except Exception as e:                          # noqa: BLE001
            out["arxiv"] = {"error": str(e)[:200]}
    return out
