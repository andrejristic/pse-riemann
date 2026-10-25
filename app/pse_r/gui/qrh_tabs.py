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
from .widgets import MarkdownView, button, hline, small


class MissionsTab(QWidget):
    """The Missions tab: question, frontier, and the step log (state→action→outcome)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        v = QVBoxLayout(self)
        top = QHBoxLayout()
        top.addWidget(QLabel("<b>Misije</b>"))
        top.addStretch(1)
        top.addWidget(button("Provjeri arXiv sada", self._arxiv_now))
        top.addWidget(button("Izvezi izvještaj misije", self._export_report))
        top.addWidget(button("Osvježi", self.refresh))
        v.addLayout(top)
        v.addWidget(hline())
        self.view = MarkdownView()
        v.addWidget(self.view, 1)
        self.refresh()

    def _arxiv_now(self):
        from ..shared_lib import runtime as RT
        r = RT.arxiv_round(force=True)
        if r.get("found", 0) == 0 and not r.get("new"):
            QMessageBox.information(self, "arXiv", "Nema novih QRH radova (ili nema mreže).")
        else:
            QMessageBox.information(
                self, "arXiv",
                f"Pronađeno {r.get('found', 0)}, novih {len(r.get('new', []))}. Novi radovi "
                f"čekaju u „Čeka tvoju odluku“: odobri izvlačenje metode.")

    def _export_report(self):
        from ..shared_lib import runtime as RT
        if not OP.current():
            QMessageBox.warning(self, "Operater", "Prvo se prijavi kao operater.")
            return
        p = RT.write_final_report(f"misije-{MIS.FIRST_ID}", self._markdown())
        QMessageBox.information(self, "Izvještaj",
                                f"Zapisan i zapečaćen:\n{p}\n\nČuvari ga od sada čuvaju.")

    def _markdown(self) -> str:
        self.refresh()
        return self._last_md

    def refresh(self):
        md = ["# Misije", ""]
        missions = MIS.all_missions()
        if not missions:
            md.append("_Nema misija._")
        for m in missions:
            best = "—" if m["best_B"] is None else f"{m['best_B']:.12f}"
            md += [f"## {m['title']}", "", f"**Pitanje.** {m['question']}", "",
                   f"**Front (najniže B).** {best}", "",
                   f"**Stanje.** {m['state']}", "", "**Koraci.**"]
            full = MIS.get(m["id"])
            steps = full["steps"] if full else []
            if not steps:
                md.append("- _(još nema koraka)_")
            for s in steps:
                md.append(f"- {s['action']} → **{s['outcome']}**")
            md.append("")
        self._last_md = "\n".join(md)
        self.view.set_markdown(self._last_md)


class QueueTab(QWidget):
    """The "Čeka tvoju odluku" queue + model chooser + import-method."""
    decided = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        v = QVBoxLayout(self)

        # model chooser (main + skeptic)
        row = QHBoxLayout()
        row.addWidget(QLabel("Glavni:"))
        self.cb_main = QComboBox()
        self.cb_skeptic = QComboBox()
        row.addWidget(self.cb_main)
        row.addWidget(QLabel("Skeptik:"))
        row.addWidget(self.cb_skeptic)
        row.addWidget(button("Primijeni", self._apply_models))
        row.addStretch(1)
        row.addWidget(button("Deklariši GGUF…", self._declare_gguf))
        row.addWidget(button("Uvezi metodu…", self._import_method, primary=True))
        v.addLayout(row)
        self.lb_models = small("")
        v.addWidget(self.lb_models)
        v.addWidget(hline())

        v.addWidget(QLabel("<b>Čeka tvoju odluku</b>"))
        self.view = MarkdownView()
        v.addWidget(self.view, 1)
        rowb = QHBoxLayout()
        self.cb_item = QComboBox()
        rowb.addWidget(self.cb_item, 1)
        rowb.addWidget(button("Odobri", lambda: self._decide(True), kind="go"))
        rowb.addWidget(button("Ne odobri", lambda: self._decide(False), kind="no"))
        v.addLayout(rowb)

        self._load_models()
        self.refresh()

    # -- models -------------------------------------------------------- #
    def _load_models(self):
        ids = [c["id"] for c in SEL.candidates()]
        self.cb_main.clear(); self.cb_skeptic.clear()
        self.cb_main.addItems(ids)
        self.cb_skeptic.addItems(["(nedostupan)"] + ids)
        main, sk = SEL.get_main(), SEL.get_skeptic()
        if main in ids:
            self.cb_main.setCurrentText(main)
        self.cb_skeptic.setCurrentText(sk if sk in ids else "(nedostupan)")
        self._show_models()

    def _show_models(self):
        main, sk = SEL.get_main(), SEL.get_skeptic()
        avail = "dostupan" if SEL.skeptic_available() else "nedostupan (samo determinističke provjere)"
        self.lb_models.setText(f"glavni: {main or '—'} · skeptik: {sk or '—'} ({avail})")

    def _apply_models(self):
        try:
            SEL.set_main(self.cb_main.currentText())
            sk = self.cb_skeptic.currentText()
            if sk and sk != "(nedostupan)":
                SEL.set_skeptic(sk)
        except ValueError as e:
            QMessageBox.warning(self, "Izbor modela", str(e))
        self._show_models()

    # -- declare a local model (master §8: the operator confirms the hash) -- #
    def _declare_gguf(self):
        from .. import config
        from ..llm import gguf as G
        path, _ = QFileDialog.getOpenFileName(self, "Deklariši lokalni model",
                                              str(config.DIR_MODELS), "GGUF (*.gguf)")
        if not path:
            return
        pub = G.PUBLISHED.get(Path(path).name)
        self.lb_models.setText("računam sha256…")
        sha = G.sha256_of(Path(path))
        note = ("odgovara objavljenom hash-u (" + pub["source"] + ")"
                if pub and pub["sha256"] == sha else
                "NEMA objavljenog hash-a za ovaj fajl — deklarišeš ga na svoju odgovornost")
        pid = G.propose_declaration(path, sha, note)
        QMessageBox.information(
            self, "Deklaracija modela",
            f"sha256: {sha}\n{note}\n\n" +
            ("Prijedlog je u redu — potvrdi ga dolje (Odobri)." if pid else
             "Prijedlog za ovaj fajl već čeka u redu."))
        self.refresh()

    # -- import a method pack through the door -------------------------- #
    def _import_method(self):
        if not OP.current():
            QMessageBox.warning(self, "Operater", "Prvo se prijavi kao operater.")
            return
        path, _ = QFileDialog.getOpenFileName(self, "Uvezi paket metode",
                                              "", "Paketi (*.json)")
        if not path:
            return
        try:
            out = DOOR.import_pack(path, proposer=f"operator:{OP.current()}",
                                   mission_id=MIS.FIRST_ID)
        except PK.PackError as e:
            QMessageBox.warning(self, "Paket metode", f"Neispravan paket: {e}")
            return
        if out["reproduced"]:
            QMessageBox.information(
                self, "Uvoz metode",
                f"Reprodukovano (B*={out['result']['computed_B']:.12f}). "
                f"Čeka tvoju potvrdu u redu.")
        else:
            r = out["result"]
            QMessageBox.warning(
                self, "Uvoz metode — odbijeno na vratima",
                f"Paket NIJE reprodukovao broj iz rada: naš pipeline daje "
                f"{r['computed_B']:.12f}, paket tvrdi {r['claimed_B']:.12f} "
                f"(razlika {r['error']:.1e}). Nije ušao u red.")
        self.refresh()

    # -- the queue ----------------------------------------------------- #
    def refresh(self):
        items = store().open_items()
        self.cb_item.clear()
        md = ["Stavke koje čekaju tvoju odluku:", ""]
        if not items:
            md.append("_Red je prazan._")
        for it in items:
            self.cb_item.addItem(f"[{it['kind']}] {it['title']}", it["id"])
            md.append(f"- **[{it['kind']}]** {it['title']} — _predložio: {it['proposer']}_")
            pl = it.get("payload") or {}
            res = pl.get("result") or {}
            if res.get("computed_B") is not None:
                md.append(f"  - reprodukcija: naš B*={res['computed_B']:.12f}, rad "
                          f"{res.get('claimed_B')}, razlika {res.get('error', 0):.1e}; "
                          f"polinom: {res.get('poly_ok')}; narušeni zidovi: "
                          f"{res.get('broken_walls') or 'nijedan'}")
            if pl.get("harms"):
                md.append(f"  - znaci zla: {', '.join(pl['harms'])}")
            if pl.get("evidence"):
                md.append(f"  - dokaz: {pl['evidence'][0][:160]}")
            if pl.get("abstract"):
                md.append(f"  - apstrakt: {pl['abstract'][:240]}…")
        self.view.set_markdown("\n".join(md))
        self._show_models()

    def _decide(self, approve: bool):
        if not OP.current():
            QMessageBox.warning(self, "Operater", "Prvo se prijavi kao operater.")
            return
        pid = self.cb_item.currentData()
        if not pid:
            return
        try:
            store().decide(pid, approve)
        except (KeyError, ValueError, OP.NoOperator) as e:
            QMessageBox.warning(self, "Odluka", str(e))
            return
        self.decided.emit()
        self.refresh()
