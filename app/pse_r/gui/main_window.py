"""
The main window — 70% workspace on the left, 30% chat on the right, and a
status bar that tells you the four things you need to know at a glance:
the source/derivation balance, the spend, the network state, and whether the
Guardian has anything to say.

Ctrl+Shift+P is the command palette (Ctrl+K is the online-AI kill switch). On a laptop keyboard on a train, a palette beats
a menu bar.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QKeySequence, QShortcut
from PySide6.QtWidgets import (QDialog, QInputDialog, QLabel, QLineEdit,
                               QListWidget, QMainWindow, QMessageBox,
                               QSplitter, QStatusBar, QTabWidget, QVBoxLayout,
                               QWidget)

from .. import config
from .. import settings as S
from ..core import briefing as BR
from ..core import journal as J
from ..core import theta as TH
from ..guardian.unit import guardian
from ..llm.budget import budget
from ..vault import index as IX
from ..vault import seed, store as VS
from .chat import ChatPanel
from .tabs import (CorpusTab, EditorTab, GraphTab, GuardianTab, LabTab, PlanTab)
from .whiteboard import WhiteboardTab
from .widgets import MarkdownView, dark_qss, set_base_pt, small


class Palette(QDialog):
    def __init__(self, actions: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Komande")
        self.resize(520, 400)
        self.actions_ = actions
        v = QVBoxLayout(self)
        self.q = QLineEdit()
        self.q.setPlaceholderText("komanda…")
        self.q.textChanged.connect(self._filter)
        self.q.returnPressed.connect(self._go)
        v.addWidget(self.q)
        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(lambda _: self._go())
        v.addWidget(self.list, 1)
        self._filter("")

    def _filter(self, text):
        self.list.clear()
        for name in self.actions_:
            if text.lower() in name.lower():
                self.list.addItem(name)
        if self.list.count():
            self.list.setCurrentRow(0)

    def _go(self):
        it = self.list.currentItem()
        if it:
            self.accept()
            self.actions_[it.text()]()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{config.APP_NAME} {config.VERSION}")
        self.resize(1420, 900)
        self.font_pt = S.base_font_pt()
        set_base_pt(self.font_pt)
        self.setStyleSheet(dark_qss(self.font_pt))

        split = QSplitter(Qt.Horizontal)
        split.setObjectName("main")
        split.setChildrenCollapsible(False)
        self.main_split = split
        self.tabs = QTabWidget()
        self.tab_plan = PlanTab()
        self.tab_lab = LabTab()
        self.tab_corpus = CorpusTab()
        self.tab_board = WhiteboardTab()
        self.tab_editor = EditorTab()
        self.tab_graph = GraphTab()
        self.tab_guard = GuardianTab()
        from .qrh_tabs import MissionsTab, QueueTab
        from .overview import OverviewTab
        self.tab_overview = OverviewTab()
        self.tab_missions = MissionsTab()
        self.tab_queue = QueueTab()
        self.tab_queue.decided.connect(self.tab_missions.refresh)
        self.tab_queue.decided.connect(self.tab_overview.refresh)
        self.tab_overview.open_queue.connect(lambda: self.tabs.setCurrentWidget(self.tab_queue))
        for w, name in ((self.tab_overview, "Pregled"),
                        (self.tab_missions, "Misije"), (self.tab_queue, "Čeka tvoju odluku"),
                        (self.tab_plan, "Plan"), (self.tab_lab, "Lab"),
                        (self.tab_corpus, "Corpus"),
                        (self.tab_board, "Tabla"), (self.tab_editor, "Editor"),
                        (self.tab_graph, "Graf"), (self.tab_guard, "Guardian")):
            self.tabs.addTab(w, name)
        split.addWidget(self.tabs)

        self.chat = ChatPanel()
        split.addWidget(self.chat)
        split.setStretchFactor(0, 7)
        split.setStretchFactor(1, 3)
        split.setSizes([int(1420 * 0.7), int(1420 * 0.3)])
        # Svarog layout: top bar with status pills above everything
        from .topbar import TopBar
        self.topbar = TopBar(self.font_pt)
        self.topbar.open_queue.connect(lambda: self.tabs.setCurrentWidget(self.tab_queue))
        self.topbar.toggle_online.connect(self.toggle_online_ai)
        central = QWidget()
        cv = QVBoxLayout(central)
        cv.setContentsMargins(0, 0, 0, 0)
        cv.setSpacing(0)
        cv.addWidget(self.topbar)
        body = QWidget()
        bv = QVBoxLayout(body)
        bv.setContentsMargins(10, 10, 10, 6)
        bv.addWidget(split)
        cv.addWidget(body, 1)
        self.setCentralWidget(central)
        self.chat.expand_toggled.connect(self.toggle_chat_expand)
        QShortcut(QKeySequence("Escape"), self, self._unexpand_chat)
        self._restore_layout()

        # wiring
        self.tab_corpus.to_context.connect(self.chat.add_context)
        self.tab_corpus.open_card.connect(self.open_card)
        self.tab_graph.open_card.connect(self.open_card)
        self.chat.open_card.connect(self.open_card)
        for sig in (self.tab_lab.card_written, self.chat.card_written,
                    self.tab_editor.card_written, self.tab_board.card_written):
            sig.connect(self.after_write)

        # status bar: messages only — the state lives in the top bar's pills
        sb = QStatusBar()
        self.setStatusBar(sb)
        self.lb_theta = QLabel("")
        self.lb_budget = QLabel("")
        self.lb_net = QLabel("")
        self.lb_guard = QLabel("")
        self.lb_vault = QLabel("")
        self.lb_ai = QLabel("")
        self.lb_op = self.topbar.pills["op"]             # kept for callers/tests
        # (legacy labels are still updated by refresh_status but not shown: the
        # top bar replaced them; network/model state is in its pills)
        self.refresh_status()
        self._start_runtime()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh_status)
        self._timer.start(15000)

        # round 3: Ctrl+K is the online-AI kill switch; the palette moved
        QShortcut(QKeySequence("Ctrl+K"), self, self.toggle_online_ai)
        QShortcut(QKeySequence("Ctrl+Shift+P"), self, self.palette_)
        # live text zoom — no restart, changes only font size
        for seq in ("Ctrl+=", "Ctrl++"):
            QShortcut(QKeySequence(seq), self, lambda: self.zoom(+0.8))
        QShortcut(QKeySequence("Ctrl+-"), self, lambda: self.zoom(-0.8))
        QShortcut(QKeySequence("Ctrl+0"), self, lambda: self.zoom(0))
        QShortcut(QKeySequence("Ctrl+S"), self, self._save_active)
        QShortcut(QKeySequence("Ctrl+1"), self,
                  lambda: self.tabs.setCurrentIndex(0))
        QShortcut(QKeySequence("Ctrl+2"), self,
                  lambda: self.tabs.setCurrentIndex(1))
        QShortcut(QKeySequence("Ctrl+3"), self,
                  lambda: self.tabs.setCurrentIndex(2))

    # ------------------------------------------------------------------ #
    def toggle_online_ai(self):
        """Ctrl+K / top-bar button: close at once; reopen only after a question."""
        from PySide6.QtWidgets import QMessageBox
        from ..guardian import killswitch as KS
        from ..shared_lib import operator as OP
        if not KS.closed():
            out = KS.close("operater (dugme / Ctrl+K)", actor=OP.current() or "operator")
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Warning)
            box.setWindowTitle("Online AI isključen")
            box.setText(f"Online AI je ISKLJUČEN. Prekinuto poziva u toku: {out['hung_up']}. "
                        f"Ključevi su sklonjeni iz memorije. Sada radi: {out['fallback']}.")
            box.setInformativeText("Da li da ključeve i TRAJNO zaboravim (obrišem iz "
                                   "secrets.json)? Tada ih moraš ponovo upisati.")
            forget = box.addButton("Zaboravi ključeve", QMessageBox.DestructiveRole)
            box.addButton("Ne, samo isključi", QMessageBox.AcceptRole)
            box.exec()
            if box.clickedButton() is forget:
                KS.close("operater: trajno zaboravi ključeve", actor=OP.current() or "operator",
                         forget_keys=True)
        else:
            r = QMessageBox.question(
                self, "Uključiti online AI?",
                f"Online AI je isključen ({KS.state().get('reason', '')}).\n\n"
                "Uključiti ponovo? Ključevi se vraćaju iz secrets.json (ako ih nisi "
                "zaboravio), a glavni AI biraš u Modeli.")
            if r == QMessageBox.Yes:
                try:
                    KS.reopen(OP.current() or "")
                except Exception as e:                       # noqa: BLE001
                    QMessageBox.warning(self, "Online AI", str(e))
        self.refresh_status()

    def palette_(self):
        acts = {
            "Online AI — isključi / uključi (Ctrl+K)": self.toggle_online_ai,
            "Podešavanje — operater, glavni AI, skeptik, čuvar": self.open_setup,
            "Lab — pokreni eksperiment": lambda: self.tabs.setCurrentIndex(1),
            "Corpus — pretraga": lambda: (self.tabs.setCurrentIndex(2),
                                          self.tab_corpus.q.setFocus()),
            "Corpus — skupi sa interneta": self.tab_corpus.harvest,
            "Corpus — trijaža": self.tab_corpus.triage,
            "Tabla — crtaj": lambda: self.tabs.setCurrentIndex(3),
            "Editor — dnevnik danas": lambda: (self.tabs.setCurrentIndex(4),
                                               self.tab_editor._daily()),
            "Graf — osvježi": lambda: (self.tabs.setCurrentIndex(5),
                                       self.tab_graph.refresh()),
            "Guardian — provjeri host": lambda: (self.tabs.setCurrentIndex(6),
                                                 self.tab_guard.refresh_host()),
            "Guardian — test mreže": lambda: (self.tabs.setCurrentIndex(6),
                                              self.tab_guard.preflight()),
            "Plan — briefing": lambda: (self.tabs.setCurrentIndex(0),
                                        self.tab_plan.refresh()),
            "Plan — sedmični izvještaj": lambda: (self.tabs.setCurrentIndex(0),
                                                  self.tab_plan.report()),
            "Vault — reindeksiraj": self.tab_corpus.reindex,
            "Vault — zasij teme (seed)": self._seed,
            "Provajderi — čarobnjak": self.open_wizard,
            "Budžet — postavi dnevni limit": self._set_cap,
            "Chat — očisti kontekst": self.chat.clear_context,
            "Prikaz — veličina interfejsa (restart)": self.set_ui_scale,
            "Prikaz — tekst veći (Ctrl +)": lambda: self.zoom(+0.8),
            "Prikaz — tekst manji (Ctrl -)": lambda: self.zoom(-0.8),
            "Prikaz — vrati podrazumijevano (Ctrl 0)": lambda: self.zoom(0),
            "Prikaz — resetuj raspored panela": self._reset_layout,
        }
        Palette(acts, self).exec()

    def zoom(self, delta: float):
        """Live text zoom. Ctrl+0 resets. Applies instantly — no restart."""
        if delta == 0:
            # clear the stored override FIRST — otherwise base_font_pt() reads
            # back the value we are trying to reset away from
            S.set_("font_pt", 0)
            self.font_pt = S.DEFAULT_FONT_PT
        else:
            step = max(1.0, self.font_pt * 0.08)   # proportional, not a flat pt
            self.font_pt = max(7.0, min(
                self.font_pt + step * (1 if delta > 0 else -1), 48.0))
            S.set_("font_pt", self.font_pt)
        set_base_pt(self.font_pt)
        self.setStyleSheet(dark_qss(self.font_pt))
        # already-rendered markdown carries its own inline sizes, so it has to
        # be laid out again or half the window ignores the change
        for v in self.findChildren(MarkdownView):
            v.rerender()
        self.statusBar().showMessage(f"veličina teksta: {self.font_pt:.1f} pt "
                                     f"(Ctrl+0 vraća na podrazumijevanu)", 3000)

    def set_ui_scale(self):
        """Whole-UI scale. Needs a restart — Qt reads it before the app exists."""
        cur = float(S.get("ui_scale", 1.0))
        v, ok = QInputDialog.getDouble(
            self, "Veličina interfejsa",
            f"Skala cijelog interfejsa (0.5–3.0).\n"
            f"Tvoj desktop prijavljuje {S.detect_desktop_scale()}×, ali "
            f"aplikacija to ignoriše i koristi samo ovaj broj.\n"
            f"1.0 = kao normalan 100% desktop.\n\n"
            f"Primjenjuje se poslije ponovnog pokretanja.",
            cur, 0.5, 3.0, 2)
        if ok:
            S.set_("ui_scale", v)
            QMessageBox.information(
                self, "Sačuvano",
                f"UI skala = {v:g}. Zatvori i pokreni ponovo.\n\n"
                f"Iz terminala odmah: ./run.sh --scale {v:g}")

    def _save_layout(self):
        try:
            S.set_("geometry", bytes(self.saveGeometry().toBase64()).decode())
            S.set_("win_state", bytes(self.saveState().toBase64()).decode())
            splits = {}
            for sp in self.findChildren(QSplitter):
                if sp.objectName():
                    splits[sp.objectName()] = sp.sizes()
            S.set_("splits", splits)
        except Exception:                                # noqa: BLE001
            pass

    def _restore_layout(self):
        from PySide6.QtCore import QByteArray
        g = S.get("geometry", "")
        if g:
            try:
                self.restoreGeometry(QByteArray.fromBase64(g.encode()))
            except Exception:                            # noqa: BLE001
                pass
        splits = S.get("splits", {}) or {}
        for sp in self.findChildren(QSplitter):
            name = sp.objectName()
            if name and name in splits and splits[name]:
                try:
                    sp.setSizes([int(x) for x in splits[name]])
                except Exception:                        # noqa: BLE001
                    pass

    def _seed(self):
        r = seed.seed_all()
        QMessageBox.information(self, "Seed", str(r))
        self.after_write()

    def _set_cap(self):
        v, ok = QInputDialog.getDouble(
            self, "Dnevni limit", "USD po danu (plaćeni provajderi):",
            budget().daily_cap, 0.0, 500.0, 2)
        if ok:
            budget().set_cap(v)
            self.refresh_status()

    def _save_active(self):
        if self.tabs.currentWidget() is self.tab_editor:
            self.tab_editor._save()

    def open_setup(self):
        from .setup import SetupDialog
        SetupDialog(self, first_run=False).exec()
        self.refresh_status()

    def open_wizard(self):
        from .wizard import Wizard
        Wizard(self).exec()
        self.refresh_status()

    # ------------------------------------------------------------------ #
    def open_card(self, card_id: str):
        from ..vault import store as _VS
        p = _VS.path_of(card_id)
        if p is None:
            self.statusBar().showMessage(f"nema kartice '{card_id}'", 4000)
            return
        self.tabs.setCurrentWidget(self.tab_editor)
        self.tab_editor.refresh()
        self.tab_editor.open_path(p)

    def after_write(self):
        self.tab_corpus.refresh()
        self.tab_plan.refresh()
        self.refresh_status()

    # ---- SHARED_LIB heartbeat + connectivity (review fix 8) -------------- #
    def _start_runtime(self):
        from ..shared_lib import runtime as RT
        from ..methods import door as DOOR
        RT.install_hooks()
        DOOR.install_hooks()
        self._online = None
        self._rt_timer = QTimer(self)
        self._rt_timer.timeout.connect(self._tick)
        self._rt_timer.start(60_000)
        self._net_timer = QTimer(self)
        self._net_timer.timeout.connect(self._check_net)
        self._net_timer.start(10 * 60_000)
        QTimer.singleShot(1500, self._tick)
        QTimer.singleShot(3000, self._check_net)

    def _tick(self):
        from ..shared_lib import runtime as RT
        try:
            out = RT.tick(online=bool(self._online))
            if out["keepers"]["tampered"]:
                self.statusBar().showMessage(
                    "⚠ čuvar: izmijenjen zapečaćen izvještaj — vraćen iz pečata", 15000)
        except Exception as e:                          # noqa: BLE001
            self.statusBar().showMessage(f"SHARED_LIB otkucaj: {e}", 8000)
        self.tab_overview.refresh()
        self.topbar.refresh()

    def _check_net(self):
        from PySide6.QtCore import QThread, QObject, Signal as _Sig

        class _W(QObject):
            done = _Sig(bool)

            def run(self):
                from ..llm import selection as SEL
                self.done.emit(SEL.main_reachable())
        if getattr(self, "_net_thread", None) is not None:
            return
        self._net_thread = QThread()
        self._net_worker = _W()
        self._net_worker.moveToThread(self._net_thread)
        self._net_thread.started.connect(self._net_worker.run)
        self._net_worker.done.connect(self._net_result)
        self._net_thread.start()

    def _net_result(self, online: bool):
        self._net_thread.quit()
        self._net_thread.wait(2000)
        self._net_thread = None
        changed = online != self._online
        self._online = online
        if changed:
            from .offline import handle_connectivity
            handle_connectivity(self, online)
            self.topbar.refresh()

    def toggle_chat_expand(self):
        exp = not self.tabs.isHidden()
        self.tabs.setVisible(not exp)
        self.chat.b_expand.setText("⤡" if exp else "⤢")

    def _unexpand_chat(self):
        if self.tabs.isHidden():
            self.toggle_chat_expand()

    def refresh_status(self):
        if hasattr(self, "topbar"):
            self.topbar.refresh()
        h = TH.meter().health()
        colour = {"healthy": "#7bc67b", "enmeshment": "#ffb74d",
                  "withdrawal": "#ffb74d", "schizoid": "#e07070"}[h["status"]]
        self.lb_theta.setText(
            f"<span style='color:{colour}'>⚖ {h['theta']:.1f}</span> "
            f"<span style='color:#777'>σ{h['sigma']:.3f}</span>")
        self.lb_theta.setToolTip(
            f"Ravnoteža izvor/izvođenje: {h['message']}\n"
            f"Zdrav opseg {h['band'][0]:.0f}–{h['band'][1]:.0f}. "
            f"Iznad = čitaš tuđe; ispod = spekulišeš bez provjere.")
        st = VS.stats()
        self.lb_vault.setText(f"📚 {st.verified}/{st.total}")
        self.lb_vault.setToolTip("provjerene / ukupno kartica")
        self.lb_budget.setText("💵 " + budget().status_line())
        self.lb_budget.setToolTip(budget().tooltip())
        g = guardian().self_check()
        if g["quarantined"]:
            self.lb_guard.setText(
                f"<span style='color:#e07070'>🛡 KARANTIN: "
                f"{', '.join(g['quarantined'])}</span>")
        elif g["problems"]:
            self.lb_guard.setText("<span style='color:#ffb74d'>🛡 provjeri</span>")
        else:
            self.lb_guard.setText(f"<span style='color:#7bc67b'>🛡 ok</span>")
        self.lb_guard.setToolTip(
            f"{g['observations']} zahtjeva · {g['tier1']} tier-1 · "
            f"{g['tier2']} tier-2")
        # main AI + skeptic pills (plan F3/F6)
        try:
            from ..llm import selection as SEL
            main = SEL.get_main() or "—"
            sk = SEL.get_skeptic() if SEL.skeptic_available() else "nedostupan"
            self.lb_ai.setText(f"🤖 {main} · 🗡 {sk}")
            self.lb_ai.setToolTip("glavni model · skeptik (uvijek drugi model)")
        except Exception:                               # noqa: BLE001
            self.lb_ai.setText("")
        from ..llm.router import router
        provs = router().available()
        self.lb_net.setText(("🔌 " + ", ".join(provs)) if provs
                            else "<span style='color:#ffb74d'>🔌 nema modela</span>")

    def _reset_layout(self):
        S.set_("splits", {})
        S.set_("geometry", "")
        QMessageBox.information(self, "Raspored",
                                "Raspored je resetovan. Vidjećeš ga poslije "
                                "ponovnog pokretanja.")

    def closeEvent(self, e):
        try:
            self._save_layout()
            TH.meter().save()
            J.log(J.SYSTEM, "app", {"event": "shutdown"})
        except Exception:                               # noqa: BLE001
            pass
        super().closeEvent(e)
