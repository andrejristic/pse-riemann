"""
The top bar (Svarog look): logo, title, and status pills you can read from
across the room — operator, balance θ, library, budget, Guardian, main AI,
skeptic, limiters, and how many things wait for your decision.

Every pill is computed from SHARED_LIB state on refresh; none is free text.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton

from .. import config
from .theme import pill_style


def _logo() -> QLabel:
    lb = QLabel()
    for p in (config.APP_ROOT / "packaging" / "pse-riemann.png",
              Path("/usr/share/icons/hicolor/256x256/apps/pse-riemann.png")):
        if p.exists():
            pm = QPixmap(str(p))
            if not pm.isNull():
                lb.setPixmap(pm.scaled(28, 28, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                break
    lb.setStyleSheet("background:transparent;")
    return lb


class TopBar(QFrame):
    open_queue = Signal()

    def __init__(self, font_pt: float, parent=None):
        super().__init__(parent)
        self.setObjectName("topbar")
        self.font_pt = font_pt
        h = QHBoxLayout(self)
        h.setContentsMargins(14, 8, 14, 8)
        h.setSpacing(8)
        h.addWidget(_logo())
        t = QLabel("PSE Riemann")
        t.setObjectName("title")
        h.addWidget(t)
        h.addStretch(1)
        self.pills: dict[str, QLabel] = {}
        for key in ("op", "theta", "vault", "budget", "guard", "main", "skeptic",
                    "limits"):
            lb = QLabel("")
            lb.setTextFormat(Qt.PlainText)
            self.pills[key] = lb
            h.addWidget(lb)
        self.queue_btn = QPushButton("")
        self.queue_btn.setProperty("kind", "primary")
        self.queue_btn.clicked.connect(self.open_queue.emit)
        h.addWidget(self.queue_btn)

    def _set(self, key: str, text: str, kind: str, tip: str = "") -> None:
        lb = self.pills[key]
        lb.setText(text)
        lb.setStyleSheet(pill_style(kind, self.font_pt))
        lb.setToolTip(tip)

    def refresh(self) -> None:
        from ..core import theta as TH
        from ..guardian.unit import guardian
        from ..llm.budget import budget
        from ..shared_lib import operator as OP
        from ..shared_lib.store import store
        from ..vault import store as VS

        op = OP.current()
        self._set("op", f"operater: {op or '—'}", "plain" if op else "danger",
                  "registrovani operater ove sesije — glas SHARED_LIB-a govori samo njemu")
        h = TH.meter().health()
        kind = {"healthy": "ok", "enmeshment": "warn", "withdrawal": "warn",
                "schizoid": "danger"}.get(h["status"], "plain")
        self._set("theta", f"θ {h['theta']:.1f}", kind,
                  f"Ravnoteža izvor/izvođenje: {h['message']} "
                  f"(zdravo {h['band'][0]:.0f}–{h['band'][1]:.0f}, σ {h['sigma']:.3f})")
        st = VS.stats()
        self._set("vault", f"kartice {st.verified}/{st.total}", "plain",
                  "provjerene / ukupno kartica")
        self._set("budget", budget().status_line(), "plain", budget().tooltip())
        g = guardian().self_check()
        if g["quarantined"]:
            self._set("guard", "Guardian: KARANTIN", "danger", ", ".join(g["quarantined"]))
        elif g["problems"]:
            self._set("guard", "Guardian: provjeri", "warn", "; ".join(map(str, g["problems"])))
        else:
            self._set("guard", "Guardian: ok", "ok",
                      f"{g['observations']} zahtjeva · {g['tier1']} tier-1 · {g['tier2']} tier-2")
        try:
            from ..llm import selection as SEL
            main = SEL.get_main()
            self._set("main", f"glavni: {main or 'nema'}", "info" if main else "warn",
                      "glavni AI radi sve uloge osim skeptika")
            if SEL.skeptic_available():
                self._set("skeptic", f"skeptik: {SEL.get_skeptic()}", "info",
                          "skeptik je uvijek drugi model; samo napada, nikad ne piše")
            else:
                self._set("skeptic", "skeptik: nedostupan", "warn",
                          "samo determinističke provjere (test reprodukcije, kapija, nivoi)")
        except Exception:                                   # noqa: BLE001
            self._set("main", "glavni: ?", "warn")
            self._set("skeptic", "skeptik: ?", "warn")
        try:
            from ..llm import limits as L
            free = L.free_ram_gb()
            danger = L.Limits().must_unload()
            self._set("limits", f"RAM {free:.1f} GB", "danger" if danger else "plain",
                      "limiteri: model se oslobađa kad slobodna memorija padne ispod praga")
        except Exception:                                   # noqa: BLE001
            self._set("limits", "limiteri: ?", "plain")
        n = len(store().open_items())
        self.queue_btn.setText(f"Čeka tvoju odluku: {n}")
        self.queue_btn.setProperty("kind", "primary" if n else "")
        self.queue_btn.style().unpolish(self.queue_btn)
        self.queue_btn.style().polish(self.queue_btn)
