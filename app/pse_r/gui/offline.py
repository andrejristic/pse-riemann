"""
No internet (plan §1, decided 2026-10-25): the app ASKS which local GGUF to use.

It counts the local models ("ima li gguf2"): with two or more the operator
picks a main and a skeptic (never the same); with one, the skeptic is
"nedostupan" and only the deterministic checks stand; with none, the AI rests
while the lab, the gate, the explorer and the keepers keep working. When the
network returns, the app asks whether to go back to the cloud main.
"""
from __future__ import annotations

from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFormLayout,
                               QLabel, QMessageBox, QVBoxLayout)

from ..llm import selection as SEL


class OfflineDialog(QDialog):
    def __init__(self, opts: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nema interneta — izaberi lokalni model")
        v = QVBoxLayout(self)
        n = len(opts["ggufs"])
        v.addWidget(QLabel(
            f"Glavni AI <b>{opts['main_was'] or '—'}</b> nije dostupan.<br>"
            f"Lokalnih GGUF modela: <b>{n}</b>. "
            + ("Možeš imati i glavnog i skeptika." if n > 1 else
               "Sa jednim modelom skeptik je <b>nedostupan</b> — ostaju samo "
               "determinističke provjere (test reprodukcije, kapija, nivoi).")))
        form = QFormLayout()
        self.main = QComboBox()
        self.main.addItems(opts["ggufs"])
        form.addRow("Glavni (lokalno):", self.main)
        self.skeptic = QComboBox()
        self.skeptic.addItem("— nedostupan —", "")
        for g in opts["ggufs"]:
            self.skeptic.addItem(g, g)
        if opts["suggest_skeptic"]:
            self.skeptic.setCurrentIndex(self.skeptic.findData(opts["suggest_skeptic"]))
        form.addRow("Skeptik (drugi model):", self.skeptic)
        v.addLayout(form)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText("Koristi lokalno")
        bb.button(QDialogButtonBox.Cancel).setText("Ostavi kako jeste")
        bb.accepted.connect(self._ok)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def _ok(self):
        main = self.main.currentText()
        sk = self.skeptic.currentData() or None
        if sk == main:
            QMessageBox.warning(self, "Skeptik", "Skeptik mora biti drugi model od glavnog.")
            return
        try:
            SEL.go_offline(main, sk)
        except ValueError as e:
            QMessageBox.warning(self, "Izbor modela", str(e))
            return
        self.accept()


def handle_connectivity(parent, online: bool) -> None:
    """Called with the result of SEL.main_reachable(); asks, never decides."""
    if not online:
        opts = SEL.offline_options()
        if not opts["ggufs"]:
            QMessageBox.information(
                parent, "Nema interneta",
                f"Glavni AI ({opts['main_was'] or '—'}) nije dostupan i nema lokalnih "
                "GGUF modela. AI miruje; lab, kapija, istraživač metoda i čuvari rade.")
            return
        OfflineDialog(opts, parent).exec()
        return
    prev = SEL.offer_restore()
    if prev and (SEL.get_main() or "").startswith("gguf:"):
        r = QMessageBox.question(parent, "Internet je tu",
                                 f"Mreža je ponovo dostupna. Vratiti {prev} kao glavni AI?")
        if r == QMessageBox.Yes:
            SEL.restore_online()
