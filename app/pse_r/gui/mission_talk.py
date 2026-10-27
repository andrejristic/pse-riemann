"""
"Razgovaraj o misiji" (plan 33f, agreement rules 28–31): the panel that opens
inside the Missions tab. Pick papers (checklist + "označi sve"), start, talk,
load a full text (arXiv only), "Sastavi zaključak". Model calls run in the
background; the window never freezes.
"""
from __future__ import annotations

import threading

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
                               QMessageBox, QTextEdit, QVBoxLayout, QWidget)

from ..i18n import tr
from ..shared_lib import mission_agent as MA
from .widgets import MarkdownView, button, flow_row, hline


class _Bridge(QObject):
    done = Signal(object, str)


class MissionTalk(QWidget):
    closed = Signal()
    proposed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.mid = None
        self.conv = None
        self._busy = False
        self._br = _Bridge()
        self._br.done.connect(self._done)
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        self.title = QLabel("")
        self.title.setWordWrap(True)
        v.addWidget(self.title)
        # step 1: choose papers
        self.pick = QWidget()
        pv = QVBoxLayout(self.pick)
        pv.setContentsMargins(0, 0, 0, 0)
        pv.addWidget(QLabel(tr("Izaberi radove (jedan, više ili sve):")))
        self.papers = QListWidget()
        pv.addWidget(self.papers, 1)
        pv.addWidget(flow_row(button(tr("Označi sve"), lambda: self._mark(True)),
                              button(tr("Odznači sve"), lambda: self._mark(False)),
                              button(tr("Počni razgovor"), self._start, primary=True),
                              button(tr("Zatvori"), self._close)))
        v.addWidget(self.pick, 1)
        # step 2: the conversation
        self.talk = QWidget()
        tv = QVBoxLayout(self.talk)
        tv.setContentsMargins(0, 0, 0, 0)
        self.view = MarkdownView()
        tv.addWidget(self.view, 1)
        self.input = QTextEdit()
        self.input.setPlaceholderText(tr("Odgovori agentu ili ga pitaj…"))
        self.input.setMaximumHeight(110)
        tv.addWidget(self.input)
        self.state = QLabel("")
        tv.addWidget(flow_row(button(tr("Pošalji"), self._say, primary=True),
                              button(tr("Puni tekst (arXiv)…"), self._fulltext),
                              button(tr("Sastavi zaključak"), self._conclude),
                              button(tr("Završi razgovor"), self._close), self.state))
        v.addWidget(self.talk, 1)
        self.talk.hide()

    # ------------------------------------------------------------------ #
    def open_for(self, mid: str) -> None:
        from ..shared_lib import missions as MIS
        m = MIS.get(mid)
        self.mid, self.conv = mid, None
        self.title.setText(tr("<b>Razgovor o misiji:</b> {0}").format(m["title"] if m else mid))
        self.papers.clear()
        for p in MA.papers(mid):
            it = QListWidgetItem(f"[{p['origin']}] {p['title'][:110]} — {p['ref']}")
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Unchecked)
            it.setData(Qt.UserRole, p["ref"])
            self.papers.addItem(it)
        if not self.papers.count():
            it = QListWidgetItem(tr("(misija još nema radova; razgovor ide samo o stanju misije)"))
            self.papers.addItem(it)
        self.pick.show()
        self.talk.hide()
        self.show()

    def _mark(self, on: bool) -> None:
        for i in range(self.papers.count()):
            it = self.papers.item(i)
            if it.data(Qt.UserRole):
                it.setCheckState(Qt.Checked if on else Qt.Unchecked)

    def _refs(self) -> list:
        return [self.papers.item(i).data(Qt.UserRole) for i in range(self.papers.count())
                if self.papers.item(i).data(Qt.UserRole)
                and self.papers.item(i).checkState() == Qt.Checked]

    def _run(self, fn, label: str) -> None:
        if self._busy:
            return
        self._busy = True
        self.state.setText(label)

        def work():
            try:
                self._br.done.emit(fn(), "")
            except Exception as e:                       # noqa: BLE001 — shown to the operator
                self._br.done.emit(None, str(e))
        threading.Thread(target=work, name="mission-talk", daemon=True).start()

    def _done(self, res, err: str) -> None:
        self._busy = False
        self.state.setText("")
        if err:
            QMessageBox.warning(self, tr("Agent misije"), err)
            return
        if isinstance(res, MA.Conversation):
            self.conv = res
        elif isinstance(res, list):                      # conclusion: queue ids
            self.proposed.emit()
        self._render()

    def _render(self) -> None:
        if self.conv is None:
            return
        self.pick.hide()
        self.talk.show()
        md = MA.to_markdown(self.conv)
        self.view.set_markdown(md)
        bar = self.view.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _start(self) -> None:
        mid, refs = self.mid, self._refs()
        self._run(lambda: MA.start(mid, refs), tr("agent čita…"))

    def _say(self) -> None:
        txt = self.input.toPlainText().strip()
        if not txt or self.conv is None:
            return
        self.input.clear()
        conv = self.conv
        self._run(lambda: MA.say(conv, txt), tr("agent razmišlja…"))

    def _fulltext(self) -> None:
        if self.conv is None:
            return
        from PySide6.QtWidgets import QInputDialog
        arx = [r for r in self.conv.refs if r.startswith("arxiv:")]
        if not arx:
            QMessageBox.information(self, tr("Puni tekst"),
                                    tr("Puni tekst postoji samo za arXiv radove; ovdje ih nema."))
            return
        ref, ok = QInputDialog.getItem(self, tr("Puni tekst"), tr("Koji rad?"), arx, 0, False)
        if ok and ref:
            conv = self.conv
            self._run(lambda: (MA.load_fulltext(conv, ref), conv)[1], tr("učitavam puni tekst…"))

    def _conclude(self) -> None:
        if self.conv is None:
            return
        conv = self.conv
        self._run(lambda: MA.conclude(conv), tr("sastavljam zaključak…"))

    def _close(self) -> None:
        self.hide()
        self.closed.emit()
