"""
The morning briefing and the weekly report.

Twenty days is long enough to lose the thread. Every launch answers three
questions before you have to ask them: what did I do yesterday, what is still
open, and what does the plan say about today. All three are derived from the
append-only journal and the vault — nothing here is a separate state file that
can drift out of sync with what actually happened.

The weekly report is the A2 pattern from the PSE Math build: a human-facing
document generated from the journal, not maintained by hand.
"""
from __future__ import annotations

import re
import time
from datetime import date, datetime, timedelta
from pathlib import Path

from .. import config
from ..vault import store as VS
from ..vault.card import COMPUTED, CITED, FOLKLORE, SPECULATION, SUSPECT
from . import journal as J

PLAN = config.VAULT / "PLAN.md"
QUESTIONS = config.VAULT / "OPEN_QUESTIONS.md"


# --------------------------------------------------------------------------- #
def _since(hours: float) -> float:
    return time.time() - hours * 3600.0


def _plan_today() -> list[str]:
    """Unchecked plan lines, earliest first — the next thing you meant to do."""
    if not PLAN.exists():
        return []
    out = []
    try:
        for line in PLAN.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^\s*-\s*\[ \]\s*(.+)$", line)
            if m:
                out.append(m.group(1).strip())
    except OSError:
        return []
    return out


def _open_questions(limit: int = 6) -> list[str]:
    out = []
    if QUESTIONS.exists():
        try:
            # questions may wrap across lines; a continuation is an indented
            # line that does not start a new bullet
            cur = None
            for line in QUESTIONS.read_text(encoding="utf-8").splitlines():
                m = re.match(r"^\s*-\s*\[ \]\s*(.+)$", line)
                if m:
                    if cur:
                        out.append(cur)
                    cur = m.group(1).strip()
                elif cur is not None and line.startswith((" ", "\t")) and line.strip():
                    cur += " " + line.strip()
                elif cur:
                    out.append(cur)
                    cur = None
            if cur:
                out.append(cur)
        except OSError:
            pass
    for c in VS.open_questions():
        out.append(f"{c.title} ({c.id})")
    return out[:limit]


def yesterday_summary(hours: float = 30.0) -> dict:
    ev = J.journal().since(_since(hours))
    labs = [e for e in ev if e["kind"] == J.LAB and e["verdict"] == "ok"]
    accepts = [e for e in ev if e["kind"] == J.GATE and e["verdict"] == "accept"]
    rejects = [e for e in ev if e["kind"] == J.GATE and e["verdict"] == "reject"]
    models = [e for e in ev if e["kind"] == J.MODEL]
    threats = [e for e in ev if e["kind"] == J.THREAT]
    ingest = [e for e in ev if e["kind"] == J.INGEST]
    spent = sum(float(e["payload"].get("usd", 0) or 0) for e in models
                if isinstance(e.get("payload"), dict))
    return {
        "lab_runs": [e["payload"].get("experiment") for e in labs],
        "cards_written": [(e["payload"].get("status"), e["payload"].get("title"))
                          for e in accepts],
        "cards_rejected": len(rejects),
        "model_calls": len(models),
        "usd": round(spent, 4),
        "threats": len(threats),
        "ingest_events": len(ingest),
    }


def _swarm() -> dict:
    """The swarm's health in one line (Faza 6d: θ is per unit)."""
    from ..shared_lib.pse_registry import pse
    sw = pse().swarm()
    msg = {"healthy": "svi zdravi", "sick": f"{sw['sick']} van zdravog obrasca",
           "measure": f"Doktorove mjere čekaju: {sw['measures']}",
           "frozen": "zamrznute: " + ", ".join(sw["frozen"])}[sw["status"]]
    return {**sw, "message": msg}


def briefing() -> str:
    """The markdown shown on launch."""
    y = yesterday_summary()
    st = VS.stats()
    h = _swarm()
    attention = VS.needs_attention()
    plan = _plan_today()
    q = _open_questions()

    L = [f"# Dobro jutro — {date.today().isoformat()}", ""]

    if y["lab_runs"] or y["cards_written"]:
        L.append("## Juče")
        if y["lab_runs"]:
            L.append(f"- Lab: {', '.join(sorted(set(y['lab_runs'])))}")
        if y["cards_written"]:
            byst: dict = {}
            for s, _ in y["cards_written"]:
                byst[s] = byst.get(s, 0) + 1
            L.append("- Kartice: " + ", ".join(f"{v}× {k}" for k, v in byst.items()))
        if y["cards_rejected"]:
            L.append(f"- Kapija je odbila {y['cards_rejected']} prijedloga")
        if y["model_calls"]:
            L.append(f"- {y['model_calls']} poziva modelu, ${y['usd']:.2f}")
        if y["threats"]:
            L.append(f"- ⚠ Guardian: {y['threats']} događaja — pogledaj tab")
        L.append("")
    else:
        L += ["## Juče", "- (ništa zabilježeno)", ""]

    L += ["## Stanje vaulta",
          f"- {st.total} kartica: **{st.verified} provjerenih** "
          f"({st.by_status.get(COMPUTED,0)} COMPUTED, "
          f"{st.by_status.get(CITED,0)} CITED), "
          f"{st.by_status.get(FOLKLORE,0)} FOLKLORE, "
          f"{st.by_status.get(SPECULATION,0)} SPECULATION, "
          f"{st.by_status.get(SUSPECT,0)} SUSPECT",
          f"- PSE roj: {h['units']} jedinica, prosječan θ {h['theta_mean']:.1f} — {h['message']}", ""]

    if attention:
        L.append("## Traži pažnju")
        for c in attention[:6]:
            why = ("skeptik je našao problem" if c.status == SUSPECT
                   else "druge kartice se oslanjaju na nju, a nema izvor")
            L.append(f"- `{c.status}` **{c.title}** — {why} (`{c.id}`)")
        L.append("")

    if q:
        L.append("## Otvorena pitanja")
        L += [f"- {x}" for x in q]
        L.append("")

    if plan:
        L.append("## Plan kaže")
        L += [f"- {x}" for x in plan[:3]]
        if len(plan) > 3:
            L.append(f"- _(još {len(plan)-3} nedovršenih stavki u PLAN.md)_")
        L.append("")

    L += ["---",
          "_Pravilo dana: bar jedan COMPUTED rezultat. Čitanje bez računanja "
          "se ne broji._"]
    return "\n".join(L)


# --------------------------------------------------------------------------- #
def daily_note(text: str = "") -> Path:
    """Create/open today's note. Written directly (notes are yours, not claims)."""
    p = config.DIR_DAILY / f"{date.today().isoformat()}.md"
    if not p.exists():
        head = (f"---\nid: {date.today().isoformat()}\n"
                f"title: Dnevnik {date.today().isoformat()}\n"
                f"type: note\nstatus: FOLKLORE\nauthor: user\n---\n\n"
                f"# {date.today().isoformat()}\n\n"
                f"## Šta sam radio\n\n\n## Šta sam naučio\n\n\n"
                f"## Zapelo\n\n\n")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(head + (text or ""), encoding="utf-8")
    elif text:
        with p.open("a", encoding="utf-8") as fh:
            fh.write("\n" + text + "\n")
    return p


def weekly_report(days: int = 7) -> str:
    """Generated from the journal — the A2 pattern: derived, never maintained."""
    ev = J.journal().since(_since(days * 24))
    per_day: dict = {}
    for e in ev:
        d = datetime.fromtimestamp(e["ts"]).date().isoformat()
        s = per_day.setdefault(d, {"lab": 0, "cards": 0, "rejects": 0,
                                   "model": 0, "usd": 0.0, "threats": 0})
        if e["kind"] == J.LAB and e["verdict"] == "ok":
            s["lab"] += 1
        elif e["kind"] == J.GATE and e["verdict"] == "accept":
            s["cards"] += 1
        elif e["kind"] == J.GATE and e["verdict"] == "reject":
            s["rejects"] += 1
        elif e["kind"] == J.MODEL:
            s["model"] += 1
            p = e.get("payload") or {}
            s["usd"] += float(p.get("usd", 0) or 0)
        elif e["kind"] == J.THREAT:
            s["threats"] += 1

    st = VS.stats()
    h = _swarm()
    L = [f"# Izvještaj — posljednjih {days} dana",
         f"_generisano {datetime.now().astimezone().isoformat(timespec='minutes')} "
         f"iz journala; ne uređuj ručno_", "",
         "| dan | lab | kartice | odbijeno | modeli | $ | prijetnje |",
         "|---|---|---|---|---|---|---|"]
    for d in sorted(per_day):
        s = per_day[d]
        L.append(f"| {d} | {s['lab']} | {s['cards']} | {s['rejects']} | "
                 f"{s['model']} | {s['usd']:.2f} | {s['threats']} |")
    tot_lab = sum(s["lab"] for s in per_day.values())
    tot_usd = sum(s["usd"] for s in per_day.values())
    L += ["", f"**Ukupno:** {tot_lab} lab pokretanja, "
              f"{sum(s['cards'] for s in per_day.values())} kartica, "
              f"${tot_usd:.2f}.", ""]

    L += ["## Vault",
          f"- {st.total} kartica, {st.verified} provjerenih, "
          f"{st.unverified} neprovjerenih",
          f"- po tipu: " + ", ".join(f"{v}× {k}" for k, v in
                                     sorted(st.by_type.items())),
          f"- PSE roj: {h['units']} jedinica, prosječan θ {h['theta_mean']:.1f} — "
          f"{h['message']}", ""]

    ok, bad = J.journal().verify_chain()
    L += ["## Integritet",
          f"- journal hash-lanac: " + ("✅ neprekinut" if ok else
                                       f"⛔ PREKINUT na događaju {bad}"),
          f"- ukupno događaja: {J.journal().count()}", ""]

    if tot_lab == 0:
        L += ["> ⚠ Nijedno lab pokretanje ove nedjelje. Ako je vault rastao "
              "samo od literature, ravnoteža ti je otišla na tuđu stranu.", ""]
    return "\n".join(L)


def write_weekly_report(days: int = 7) -> Path:
    p = config.DIR_DAILY / f"izvjestaj-{date.today().isoformat()}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(weekly_report(days), encoding="utf-8")
    J.log(J.SYSTEM, "report", {"path": str(p), "days": days})
    return p
