"""Round 3, item 24: SR/EN for the whole interface."""
import re

from pse_r import i18n
from pse_r.guardian import templates as T
from pse_r.i18n_en import EN
from pse_r.i18n_strings import STRINGS


def test_every_string_translated_with_same_placeholders():
    assert not i18n.missing()
    for s in STRINGS:
        assert sorted(re.findall(r"\{[^}]*\}", s)) == sorted(re.findall(r"\{[^}]*\}", EN[s])), s


def test_switch_and_templates(monkeypatch):
    monkeypatch.setattr(i18n, "_LANG", "en")
    assert i18n.tr("Odobri") == "Approve"
    assert i18n.tr("Čeka tvoju odluku: {0}").format(3) == "Awaiting your decision: 3"
    assert i18n.tr("tekst koji ne postoji") == "tekst koji ne postoji"
    assert "BLOCKED" in T.render("ssh.blocked", ip="203.0.113.9", target="root", until="sutra")
    monkeypatch.setattr(i18n, "_LANG", "sr")
    assert i18n.tr("Odobri") == "Odobri"
    assert "BLOKIRAN" in T.render("ssh.blocked", ip="203.0.113.9", target="root", until="sutra")


def test_main_window_builds_in_english(operator, monkeypatch):
    monkeypatch.setattr(i18n, "_LANG", "en")
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from pse_r.gui.main_window import MainWindow
    w = MainWindow()
    titles = [w.tabs.tabText(i) for i in range(w.tabs.count())]
    assert "Overview" in titles and "Awaiting your decision" in titles
    import shiboken6
    shiboken6.delete(w)
