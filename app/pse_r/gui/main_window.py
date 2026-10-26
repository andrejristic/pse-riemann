"""
The main window — 70% workspace on the left, 30% chat on the right, and a
status bar that tells you the four things you need to know at a glance:
the source/derivation balance, the spend, the network state, and whether the
Guardian has anything to say.

Ctrl+Shift+P is the command palette (Ctrl+K is the online-AI kill switch). On a laptop keyboard on a train, a palette beats
a menu bar.
"""
from __future__ import annotations

from ..i18n import tr

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
        self.setWindowTitle(tr("Komande"))
        self.resize(520, 400)
        self.actions_ = actions
        v = QVBoxLayout(self)
        self.q = QLineEdit()
        self.q.setPlaceholderText(tr("komanda…"))
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
        for w, name in ((self.tab_overview, tr("Pregled")),
                        (self.tab_missions, tr("Misije")), (self.tab_queue, tr("Čeka tvoju odluku")),
                        (self.tab_plan, tr("Plan")), (self.tab_lab, tr("Lab")),
                        (self.tab_corpus, tr("Corpus")),
                        (self.tab_board, tr("Tabla")), (self.tab_editor, tr("Editor")),
                        (self.tab_graph, tr("Graf")), (self.tab_guard, tr("Guardian"))):
            self.tabs.addTab(w, tr(name))
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
        self.topbar.toggle_lang.connect(self.toggle_language)
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
    def toggle_language(self):
        """SR/EN for the whole interface (round 3, item 23): saved, then the
        window is reopened in the new language (one restart, no half-translated UI)."""
        import sys
        from PySide6.QtCore import QProcess
        from PySide6.QtWidgets import QMessageBox
        from .. import i18n
        new = "en" if i18n.lang() == "sr" else "sr"
        i18n.set_lang(new)
        r = QMessageBox.question(self, "SR / EN",
                                 "Interface language: English. Restart now?" if new == "en"
                                 else "Jezik interfejsa: srpski. Ponovo pokrenuti sada?")
        if r == QMessageBox.Yes:
            self._closing_confirmed = True              # the guardian keeps running
            QProcess.startDetached(sys.executable, sys.argv)
            self.close()

    def toggle_online_ai(self):
        """Ctrl+K / top-bar button: close at once; reopen only after a question."""
        from PySide6.QtWidgets import QMessageBox
        from ..guardian import killswitch as KS
        from ..shared_lib import operator as OP
        if not KS.closed():
            out = KS.close("operater (dugme / Ctrl+K)", actor=OP.current() or "operator")
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Warning)
            box.setWindowTitle(tr("Online AI isključen"))
            box.setText(tr("Online AI je ISKLJUČEN. Prekinuto poziva u toku: {0}. Ključevi su sklonjeni iz memorije. Sada radi: {1}.").format(out['hung_up'], out['fallback']))
            box.setInformativeText(tr("Da li da ključeve i TRAJNO zaboravim (obrišem iz "
                                   "secrets.json)? Tada ih moraš ponovo upisati."))
            forget = box.addButton(tr("Zaboravi ključeve"), QMessageBox.DestructiveRole)
            box.addButton(tr("Ne, samo isključi"), QMessageBox.AcceptRole)
            box.exec()
            if box.clickedButton() is forget:
                KS.close("operater: trajno zaboravi ključeve", actor=OP.current() or "operator",
                         forget_keys=True)
        else:
            r = QMessageBox.question(
                self, tr("Uključiti online AI?"),
                tr("Online AI je isključen ({0}).\n\nUključiti ponovo? Ključevi se vraćaju iz secrets.json (ako ih nisi zaboravio), a glavni AI biraš u Modeli.").format(KS.state().get('reason', '')))
            if r == QMessageBox.Yes:
                try:
                    KS.reopen(OP.current() or "")
                except Exception as e:                       # noqa: BLE001
                    QMessageBox.warning(self, tr("Online AI"), str(e))
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
        acts = {tr(k): v for k, v in acts.items()}
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
        self.statusBar().showMessage(tr("veličina teksta: {0:.1f} pt (Ctrl+0 vraća na podrazumijevanu)").format(self.font_pt), 3000)

    def set_ui_scale(self):
        """Whole-UI scale. Needs a restart — Qt reads it before the app exists."""
        cur = float(S.get("ui_scale", 1.0))
        v, ok = QInputDialog.getDouble(
            self, tr("Veličina interfejsa"),
            tr("Skala cijelog interfejsa (0.5–3.0).\nTvoj desktop prijavljuje {0}×, ali aplikacija to ignoriše i koristi samo ovaj broj.\n1.0 = kao normalan 100% desktop.\n\nPrimjenjuje se poslije ponovnog pokretanja.").format(S.detect_desktop_scale()),
            cur, 0.5, 3.0, 2)
        if ok:
            S.set_("ui_scale", v)
            QMessageBox.information(
                self, tr("Sačuvano"),
                tr("UI skala = {0:g}. Zatvori i pokreni ponovo.\n\nIz terminala odmah: ./run.sh --scale {1:g}").format(v, v))

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
        QMessageBox.information(self, tr("Seed"), str(r))
        self.after_write()

    def _set_cap(self):
        v, ok = QInputDialog.getDouble(
            self, tr("Dnevni limit"), tr("USD po danu (plaćeni provajderi):"),
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
            self.statusBar().showMessage(tr("nema kartice '{0}'").format(card_id), 4000)
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
        from ..shared_lib import missions as _MIS
        _MIS.install_hooks()
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
                    tr("⚠ čuvar: izmijenjen zapečaćen izvještaj — vraćen iz pečata"), 15000)
        except Exception as e:                          # noqa: BLE001
            self.statusBar().showMessage(tr("SHARED_LIB otkucaj: {0}").format(e), 8000)
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
        try:
            from .danger import show_if_pending
            show_if_pending(self)                       # item 16: never silent
        except Exception:                               # noqa: BLE001
            pass
        if hasattr(self, "topbar"):
            self.topbar.refresh()
        h = TH.meter().health()
        colour = {"healthy": "#7bc67b", "enmeshment": "#ffb74d",
                  "withdrawal": "#ffb74d", "schizoid": "#e07070"}[h["status"]]
        self.lb_theta.setText(
            tr("<span style='color:{0}'>⚖ {1:.1f}</span> <span style='color:#777'>σ{2:.3f}</span>").format(colour, h['theta'], h['sigma']))
        self.lb_theta.setToolTip(
            tr("Ravnoteža izvor/izvođenje: {0}\nZdrav opseg {1:.0f}–{2:.0f}. Iznad = čitaš tuđe; ispod = spekulišeš bez provjere.").format(h['message'], h['band'][0], h['band'][1]))
        st = VS.stats()
        self.lb_vault.setText(f"📚 {st.verified}/{st.total}")
        self.lb_vault.setToolTip(tr("provjerene / ukupno kartica"))
        self.lb_budget.setText("💵 " + budget().status_line())
        self.lb_budget.setToolTip(budget().tooltip())
        g = guardian().self_check()
        if g["quarantined"]:
            self.lb_guard.setText(
                tr("<span style='color:#e07070'>🛡 KARANTIN: {0}</span>").format(', '.join(g['quarantined'])))
        elif g["problems"]:
            self.lb_guard.setText(tr("<span style='color:#ffb74d'>🛡 provjeri</span>"))
        else:
            self.lb_guard.setText(tr("<span style='color:#7bc67b'>🛡 ok</span>").format())
        self.lb_guard.setToolTip(
            tr("{0} zahtjeva · {1} tier-1 · {2} tier-2").format(g['observations'], g['tier1'], g['tier2']))
        # main AI + skeptic pills (plan F3/F6)
        try:
            from ..llm import selection as SEL
            main = SEL.get_main() or "—"
            sk = SEL.get_skeptic() if SEL.skeptic_available() else "nedostupan"
            self.lb_ai.setText(f"🤖 {main} · 🗡 {sk}")
            self.lb_ai.setToolTip(tr("glavni model · skeptik (uvijek drugi model)"))
        except Exception:                               # noqa: BLE001
            self.lb_ai.setText("")
        from ..llm.router import router
        provs = router().available()
        self.lb_net.setText(("🔌 " + ", ".join(provs)) if provs
                            else tr("<span style='color:#ffb74d'>🔌 nema modela</span>"))

    def _reset_layout(self):
        S.set_("splits", {})
        S.set_("geometry", "")
        QMessageBox.information(self, tr("Raspored"),
                                tr("Raspored je resetovan. Vidjećeš ga poslije "
                                "ponovnog pokretanja."))

    def closeEvent(self, e):
        # round 3, item 19: the guardian is a separate process — ask what to close
        if not getattr(self, "_closing_confirmed", False):
            from PySide6.QtWidgets import QMessageBox
            from .. import guardian_app as GA
            if GA.running_pid():
                box = QMessageBox(self)
                box.setWindowTitle(tr("Zatvaranje"))
                box.setText(tr("Čuvar (SSH + prekidač) radi kao poseban proces."))
                b_all = box.addButton(tr("Ugasi sve"), QMessageBox.DestructiveRole)
                b_win = box.addButton(tr("Zatvori prozor, čuvar ostaje"), QMessageBox.AcceptRole)
                box.addButton(tr("Odustani"), QMessageBox.RejectRole)
                box.setDefaultButton(b_win)
                box.exec()
                if box.clickedButton() is b_all:
                    GA.stop()
                elif box.clickedButton() is not b_win:
                    e.ignore()
                    return
        th = getattr(self, "_net_thread", None)          # no QThread left running at exit
        if th is not None:
            th.quit()
            th.wait(3000)
        try:
            self._save_layout()
            TH.meter().save()
            J.log(J.SYSTEM, "app", {"event": "shutdown"})
        except Exception:                               # noqa: BLE001
            pass
        super().closeEvent(e)
