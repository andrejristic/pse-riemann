"""
QRH tabs (plan F6): the Missions tab and the "Čeka tvoju odluku" queue.

Missions shows the standing question, the frontier B it has reached, and the
log of {state, action, outcome} steps — the heart of the project (plan §0).

The queue is the single place where everything that needs the operator waits:
method proposals (reproduced, awaiting confirmation), skeptic objections,
declarations, and tier-2 healing actions. Approve / Ne odobri call the SAME
store().decide the backend uses, so a click here is a real, journalled decision
bound to the operator's name. "Uvezi metodu" sends a method pack through the
door (reproduction test first). A small chooser picks the main and skeptic
models.

The visual styling is the shared dark QSS; nothing here needs its own look.
"""
from __future__ import annotations

from ..i18n import tr

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QComboBox, QFileDialog, QHBoxLayout, QLabel,
                               QMessageBox, QVBoxLayout, QWidget)

from ..shared_lib import missions as MIS
from ..shared_lib import operator as OP
from ..shared_lib.store import store
from ..methods import door as DOOR
from ..methods import pack as PK
from ..llm import selection as SEL
from .widgets import MarkdownView, button, flow_row, hline, short_combo, small


class MissionsTab(QWidget):
    """The Missions tab: question, frontier, and the step log (state→action→outcome)."""
    switched = Signal()                 # item 28a: the active mission changed

    def __init__(self, parent=None):
        super().__init__(parent)
        v = QVBoxLayout(self)
        v.addWidget(flow_row(QLabel(tr("<b>Misije</b>")),
                             button(tr("Provjeri arXiv sada"), self._arxiv_now),
                             button(tr("Izvezi izvještaj misije"), self._export_report),
                             button(tr("Adversarijalni mod…"), self._adversary),
                             button(tr("Osvježi"), self.refresh)))
        # round 3, items 26–27: the mission goal is ALWAYS the operator's choice, here
        self.cb_mission = QComboBox()
        self.cb_goal = QComboBox()
        short_combo(self.cb_mission, 22)
        short_combo(self.cb_goal, 18)
        for g, txt in MIS.GOALS.items():
            self.cb_goal.addItem(f"{g} · {tr(txt)}", g)
        self.cb_mission.currentIndexChanged.connect(self._show_goal)
        v.addWidget(flow_row(QLabel(tr("Cilj misije:")), self.cb_mission, self.cb_goal,
                             button(tr("Primijeni cilj"), self._apply_goal)))
        # round 3, item 28a: one active mission; park the others "for later"
        self.lb_active = QLabel("")
        self.lb_active.setWordWrap(True)
        self.cb_bg = QComboBox()
        short_combo(self.cb_bg, 16)
        for k, txt in MIS.BACKGROUND.items():
            self.cb_bg.addItem(tr(txt), k)
        self.cb_bg.activated.connect(self._apply_bg)
        v.addWidget(self.lb_active)
        v.addWidget(flow_row(button(tr("Pređi na izabranu"), self._switch_selected),
                             button(tr("Sljedeća misija ⟳"), self._switch_next),
                             button(tr("Ostavi za kasnije…"), self._park_active),
                             QLabel(tr("Dok čeka:")), self.cb_bg))
        self._card_md = ""
        v.addWidget(hline())
        self.view = MarkdownView()
        v.addWidget(self.view, 1)
        self.refresh()

    def _show_goal(self):
        mid = self.cb_mission.currentData()
        m = MIS.get(mid) if mid else None
        if m:
            i = self.cb_goal.findData(int(m.get("goal") or 1))
            self.cb_goal.setCurrentIndex(max(0, i))
            if hasattr(self, "cb_bg"):
                self.cb_bg.setCurrentIndex(max(0, self.cb_bg.findData(MIS.background(mid))))

    # ---- missions in turn (item 28a) ---------------------------------- #
    def _ask_note(self) -> "str | None":
        from PySide6.QtWidgets import QInputDialog
        cur = MIS.get(MIS.active() or "")
        txt, ok = QInputDialog.getMultiLineText(
            self, tr("Ostavi za kasnije"),
            tr("Gdje si stao u misiji „{0}“? (jedna rečenica za sebe; front, koraci i otvorene stavke se pamte sami)").format(cur["title"] if cur else "—"))
        return txt if ok else None

    def _switch_to(self, mid):
        note = self._ask_note() if mid != MIS.active() else ""
        if note is None:
            return
        try:
            card = MIS.set_active(mid, note)
        except Exception as e:                       # noqa: BLE001 — shown, nothing changed
            QMessageBox.warning(self, tr("Misije"), str(e))
            return
        self._card_md = where_md(card)
        self.refresh()
        self.switched.emit()

    def _switch_selected(self):
        mid = self.cb_mission.currentData()
        if mid:
            self._switch_to(mid)

    def _switch_next(self):
        mid = MIS.next_id()
        if mid:
            self._switch_to(mid)

    def _park_active(self):
        mid = MIS.active()
        note = self._ask_note()
        if not mid or note is None:
            return
        try:
            MIS.park(mid, note)
        except Exception as e:                       # noqa: BLE001
            QMessageBox.warning(self, tr("Misije"), str(e))
            return
        self._card_md = tr("_Misija „{0}“ je ostavljena za kasnije. Izaberi drugu ili je nastavi sa „Pređi na izabranu“._").format(MIS.get(mid)["title"])
        self.refresh()
        self.switched.emit()

    def _apply_bg(self):
        mid = self.cb_mission.currentData()
        if not mid:
            return
        try:
            MIS.set_background(mid, self.cb_bg.currentData())
        except Exception as e:                       # noqa: BLE001
            QMessageBox.warning(self, tr("Misije"), str(e))
        self.refresh()

    def _apply_goal(self):
        mid, g = self.cb_mission.currentData(), self.cb_goal.currentData()
        if not mid:
            return
        try:
            MIS.set_goal(mid, int(g), "izbor operatera u meniju misije")
        except Exception as e:                       # noqa: BLE001 — shown, nothing changed
            QMessageBox.warning(self, tr("Cilj misije"), str(e))
            return
        self.refresh()

    def _adversary(self):
        """Item 31: attack a method's claim with numbers (background; result in the queue)."""
        from PySide6.QtWidgets import QInputDialog
        from ..methods import adversary as ADV
        from ..methods import registry as R
        names = []
        for m in R.KNOWN:
            try:
                ADV.family(m.name)
                names.append(m.name)
            except (KeyError, ValueError):
                continue
        if not names:
            QMessageBox.information(self, tr("Adversarijalni mod"), tr("Nema metode sa funkcijom eksponenta."))
            return
        name, ok = QInputDialog.getItem(self, tr("Adversarijalni mod"),
                                        tr("Koju tvrdnju da napadnem brojevima? (~5–15 s u pozadini; rezultat ide u „Čeka tvoju odluku“, na Grafove i u Lab)"),
                                        names, 0, False)
        if ok and name:
            ADV.attack_in_background(name)
            QMessageBox.information(self, tr("Adversarijalni mod"),
                                    tr("Pokrenuto za „{0}“. Nalaz stiže u „Čeka tvoju odluku“.").format(name))

    def _arxiv_now(self):
        from ..shared_lib import runtime as RT
        r = RT.arxiv_round(force=True)
        if r.get("found", 0) == 0 and not r.get("new"):
            QMessageBox.information(self, tr("arXiv"), tr("Nema novih QRH radova (ili nema mreže)."))
        else:
            QMessageBox.information(
                self, tr("arXiv"),
                tr("Pronađeno {0}, novih {1}. Novi radovi čekaju u „Čeka tvoju odluku“: odobri izvlačenje metode.").format(r.get('found', 0), len(r.get('new', []))))

    def _export_report(self):
        from ..shared_lib import runtime as RT
        if not OP.current():
            QMessageBox.warning(self, tr("Operater"), tr("Prvo se prijavi kao operater."))
            return
        p = RT.write_final_report(f"misije-{MIS.FIRST_ID}", self._markdown())
        QMessageBox.information(self, tr("Izvještaj"),
                                tr("Zapisan i zapečaćen:\n{0}\n\nČuvari ga od sada čuvaju.").format(p))

    def _markdown(self) -> str:
        self.refresh()
        return self._last_md

    def refresh(self):
        md = [tr("# Misije"), ""]
        missions = MIS.all_missions()
        if hasattr(self, "cb_mission"):
            cur = self.cb_mission.currentData()
            self.cb_mission.blockSignals(True)
            self.cb_mission.clear()
            for m in missions:
                self.cb_mission.addItem(m["title"], m["id"])
            self.cb_mission.setCurrentIndex(max(0, self.cb_mission.findData(cur)))
            self.cb_mission.blockSignals(False)
            self._show_goal()
        act = MIS.active()
        if hasattr(self, "lb_active"):
            am = MIS.get(act) if act else None
            self.lb_active.setText(tr("<b>Aktivna:</b> {0}").format(am["title"] if am else "—")
                                   + (tr(" <i>(ostavljena za kasnije)</i>") if am and int(am.get("parked") or 0) else ""))
        if getattr(self, "_card_md", ""):
            md += [self._card_md, "", "---", ""]
        if not missions:
            md.append(tr("_Nema misija._"))
        for m in missions:
            best = "—" if m["best_B"] is None else f"{m['best_B']:.12f}"
            mark = (tr(" · ▶ aktivna") if m["id"] == act and not int(m.get("parked") or 0) else
                    tr(" · ⏸ za kasnije") if int(m.get("parked") or 0) else "")
            md += [f"## {m['title']}{mark}", "", tr("**Pitanje.** {0}").format(m['question']), "",
                   tr("**Front (najniže B).** {0}").format(best), "",
                   tr("**Cilj.** {0}").format(tr(MIS.GOALS.get(int(m.get("goal") or 1), ""))), "",
                   tr("**Stanje.** {0}").format(m['state']), "", tr("**Koraci.**")]
            full = MIS.get(m["id"])
            steps = full["steps"] if full else []
            if not steps:
                md.append(tr("- _(još nema koraka)_"))
            for s in steps:
                md.append(f"- {s['action']} → **{s['outcome']}**")
            md.append("")
        self._last_md = "\n".join(md)
        self.view.set_markdown(self._last_md)


def where_md(card: dict) -> str:
    """The "Gdje si stao" card as Markdown (item 28a)."""
    import time as _t
    out = [tr("### Gdje si stao: {0}").format(card["title"]), ""]
    if card.get("parked_at"):
        out.append(tr("Ostavljeno: {0}").format(_t.strftime("%Y-%m-%d %H:%M", _t.localtime(card["parked_at"]))))
    out.append(tr("**Tvoja bilješka:** {0}").format(card["note"] or tr("_(bez bilješke)_")))
    snap = card.get("snapshot") or {}
    if snap:
        best = "—" if snap.get("best_B") is None else f"{snap['best_B']:.9f}"
        out.append(tr("**Tada:** front B = {0}, cilj {1}, koraka {2}.").format(best, snap.get("goal"), snap.get("n_steps")))
        if snap.get("last_step"):
            out.append(tr("**Zadnji korak:** {0} → {1}").format(snap["last_step"]["action"], snap["last_step"]["outcome"]))
    out.append("")
    since, rel = card.get("steps_since") or [], card.get("released") or []
    oi = (card.get("now") or {}).get("open_items") or []
    if not since and not rel:
        out.append(tr("**Dok te nije bilo:** ništa novo") + (tr(" (misija je bila zamrznuta).") if card.get("background") == MIS.FREEZE else "."))
    else:
        out.append(tr("**Dok te nije bilo:** {0} novih koraka, {1} radova sa arXiv-a (sada u „Čeka tvoju odluku“).").format(len(since), len(rel)))
        for st in since[-5:]:
            out.append(f"- {st['action']} → **{st['outcome']}**")
    if oi:
        out.append(tr("**Otvoreno u redu za ovu misiju:** {0}").format(len(oi)))
    return "\n".join(out)


class QueueTab(QWidget):
    """The "Čeka tvoju odluku" queue + model chooser + import-method."""
    decided = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        v = QVBoxLayout(self)

        # model chooser (main + skeptic)
        row = QHBoxLayout()
        row.addWidget(QLabel(tr("Glavni:")))
        self.cb_main = QComboBox()
        self.cb_skeptic = QComboBox()
        row.addWidget(self.cb_main)
        row.addWidget(QLabel(tr("Skeptik:")))
        row.addWidget(self.cb_skeptic)
        row.addWidget(button(tr("Primijeni"), self._apply_models))
        row.addStretch(1)
        row.addWidget(button(tr("Deklariši GGUF…"), self._declare_gguf))
        row.addWidget(button(tr("Uvezi metodu…"), self._import_method, primary=True))
        v.addLayout(row)
        self.lb_models = small("")
        v.addWidget(self.lb_models)
        v.addWidget(hline())

        v.addWidget(QLabel(tr("<b>Čeka tvoju odluku</b>")))
        self.view = MarkdownView()
        v.addWidget(self.view, 1)
        rowb = QHBoxLayout()
        self.cb_item = QComboBox()
        rowb.addWidget(self.cb_item, 1)
        rowb.addWidget(button(tr("Odobri"), lambda: self._decide(True), kind="go"))
        rowb.addWidget(button(tr("Ne odobri"), lambda: self._decide(False), kind="no"))
        v.addLayout(rowb)

        self._load_models()
        self.refresh()

    # -- models -------------------------------------------------------- #
    def _load_models(self):
        ids = [c["id"] for c in SEL.candidates()]
        self.cb_main.clear(); self.cb_skeptic.clear()
        self.cb_main.addItems(ids)
        self.cb_skeptic.addItems([tr("(nedostupan)")] + ids)
        main, sk = SEL.get_main(), SEL.get_skeptic()
        if main in ids:
            self.cb_main.setCurrentText(main)
        self.cb_skeptic.setCurrentText(sk if sk in ids else tr("(nedostupan)"))
        self._show_models()

    def _show_models(self):
        main, sk = SEL.get_main(), SEL.get_skeptic()
        avail = tr("dostupan") if SEL.skeptic_available() else tr("nedostupan (samo determinističke provjere)")
        self.lb_models.setText(tr("glavni: {0} · skeptik: {1} ({2})").format(main or '—', sk or '—', avail))

    def _apply_models(self):
        try:
            SEL.set_main(self.cb_main.currentText())
            sk = self.cb_skeptic.currentText()
            if sk and sk != tr("(nedostupan)"):
                SEL.set_skeptic(sk)
        except ValueError as e:
            QMessageBox.warning(self, tr("Izbor modela"), str(e))
        self._show_models()

    # -- declare a local model (master §8: the operator confirms the hash) -- #
    def _declare_gguf(self):
        from .. import config
        from ..llm import gguf as G
        path, _ = QFileDialog.getOpenFileName(self, tr("Deklariši lokalni model"),
                                              str(config.DIR_MODELS), "GGUF (*.gguf)")
        if not path:
            return
        pub = G.PUBLISHED.get(Path(path).name)
        self.lb_models.setText(tr("računam sha256…"))
        sha = G.sha256_of(Path(path))
        note = (tr("odgovara objavljenom hash-u (") + pub["source"] + ")"
                if pub and pub["sha256"] == sha else
                tr("NEMA objavljenog hash-a za ovaj fajl — deklarišeš ga na svoju odgovornost"))
        pid = G.propose_declaration(path, sha, note)
        QMessageBox.information(
            self, tr("Deklaracija modela"),
            f"sha256: {sha}\n{note}\n\n" +
            (tr("Prijedlog je u redu — potvrdi ga dolje (Odobri).") if pid else
             tr("Prijedlog za ovaj fajl već čeka u redu.")))
        self.refresh()

    # -- import a method pack through the door -------------------------- #
    def _import_method(self):
        if not OP.current():
            QMessageBox.warning(self, tr("Operater"), tr("Prvo se prijavi kao operater."))
            return
        path, _ = QFileDialog.getOpenFileName(self, tr("Uvezi paket metode"),
                                              "", "Paketi (*.json)")
        if not path:
            return
        try:
            out = DOOR.import_pack(path, proposer=f"operator:{OP.current()}",
                                   mission_id=MIS.FIRST_ID)
        except PK.PackError as e:
            QMessageBox.warning(self, tr("Paket metode"), tr("Neispravan paket: {0}").format(e))
            return
        if out["reproduced"]:
            QMessageBox.information(
                self, tr("Uvoz metode"),
                tr("Reprodukovano (B*={0:.12f}). Čeka tvoju potvrdu u redu.").format(out['result']['computed_B']))
        else:
            r = out["result"]
            QMessageBox.warning(
                self, tr("Uvoz metode — odbijeno na vratima"),
                tr("Paket NIJE reprodukovao broj iz rada: naš pipeline daje {0:.12f}, paket tvrdi {1:.12f} (razlika {2:.1e}). Nije ušao u red.").format(r['computed_B'], r['claimed_B'], r['error']))
        self.refresh()

    # -- the queue ----------------------------------------------------- #
    def refresh(self):
        items = store().open_items()
        self.cb_item.clear()
        md = [tr("Stavke koje čekaju tvoju odluku:"), ""]
        if not items:
            md.append(tr("_Red je prazan._"))
        for it in items:
            self.cb_item.addItem(f"[{it['kind']}] {it['title']}", it["id"])
            md.append(tr("- **[{0}]** {1} — _predložio: {2}_").format(it['kind'], it['title'], it['proposer']))
            pl = it.get("payload") or {}
            res = pl.get("result") or {}
            if res.get("computed_B") is not None:
                md.append(tr("  - reprodukcija: naš B*={0:.12f}, rad {1}, razlika {2:.1e}; polinom: {3}; narušeni zidovi: {4}").format(res['computed_B'], res.get('claimed_B'), res.get('error', 0), res.get('poly_ok'), res.get('broken_walls') or 'nijedan'))
            if pl.get("harms"):
                md.append(tr("  - znaci zla: {0}").format(', '.join(pl['harms'])))
            if pl.get("evidence"):
                md.append(tr("  - dokaz: {0}").format(pl['evidence'][0][:160]))
            if pl.get("abstract"):
                md.append(tr("  - apstrakt: {0}…").format(pl['abstract'][:240]))
        self.view.set_markdown("\n".join(md))
        self._show_models()

    def _decide(self, approve: bool):
        if not OP.current():
            QMessageBox.warning(self, tr("Operater"), tr("Prvo se prijavi kao operater."))
            return
        pid = self.cb_item.currentData()
        if not pid:
            return
        try:
            store().decide(pid, approve)
        except (KeyError, ValueError, OP.NoOperator) as e:
            QMessageBox.warning(self, tr("Odluka"), str(e))
            return
        self.decided.emit()
        self.refresh()
