"""
Pregled (overview) — the first tab, Svarog style: metric tiles, the mission
front, what waits for the operator, and the latest events. Every number here is
ONE read-only SELECT over the SHARED_LIB fact views (shared_lib.views), so the
overview can never say anything the library does not contain.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel, QVBoxLayout,
                               QWidget)

from .widgets import MarkdownView, button


def _metric(key: str) -> tuple[QFrame, QLabel]:
    f = QFrame()
    f.setObjectName("metric")
    v = QVBoxLayout(f)
    v.setContentsMargins(14, 10, 14, 10)
    k = QLabel(key)
    k.setObjectName("metricK")
    val = QLabel("…")
    val.setObjectName("metricV")
    v.addWidget(k)
    v.addWidget(val)
    return f, val


def _card(title: str) -> tuple[QFrame, MarkdownView]:
    f = QFrame()
    f.setObjectName("card")
    v = QVBoxLayout(f)
    v.setContentsMargins(14, 10, 14, 10)
    h = QLabel(title)
    h.setObjectName("cardH")
    v.addWidget(h)
    md = MarkdownView()
    v.addWidget(md, 1)
    return f, md


Q = {
    "kartice": "SELECT COUNT(*) FROM cards",
    "provjerene": "SELECT COUNT(*) FROM cards WHERE status IN ('CITED','COMPUTED')",
    "lab": "SELECT COUNT(*) FROM lab_runs",
    "događaji": "SELECT COUNT(*) FROM events",
    "čeka": "SELECT COUNT(*) FROM pending WHERE status='open'",
    "metode": "SELECT COUNT(*) FROM events WHERE kind='method' AND verdict='accept'",
    "pečati": "SELECT COUNT(*) FROM seals",
    "front": "SELECT MIN(best_B) FROM missions",
}


class OverviewTab(QWidget):
    open_queue = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        v = QVBoxLayout(self)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(12)
        top = QHBoxLayout()
        top.addWidget(QLabel("<b>Pregled</b> — sve brojke su upiti nad SHARED_LIB-om"))
        top.addStretch(1)
        top.addWidget(button("Osvježi", self.refresh))
        v.addLayout(top)

        grid = QGridLayout()
        grid.setSpacing(11)
        self.vals: dict[str, QLabel] = {}
        labels = [("front", "front misije (najniže B)"), ("čeka", "čeka tvoju odluku"),
                  ("metode", "potvrđene metode"), ("pečati", "zapečaćeni izvještaji"),
                  ("kartice", "kartice"), ("provjerene", "provjerene (CITED/COMPUTED)"),
                  ("lab", "lab run-ova"), ("događaji", "događaja u dnevniku")]
        for i, (key, lab) in enumerate(labels):
            f, val = _metric(lab)
            self.vals[key] = val
            grid.addWidget(f, i // 4, i % 4)
        v.addLayout(grid)

        row = QHBoxLayout()
        row.setSpacing(12)
        f1, self.md_queue = _card("Čeka tvoju odluku")
        f2, self.md_events = _card("Zadnji događaji")
        row.addWidget(f1, 1)
        row.addWidget(f2, 1)
        v.addLayout(row, 1)
        b = button("Otvori red odluka", self.open_queue.emit, kind="primary")
        v.addWidget(b, 0, Qt.AlignRight)
        self.refresh()

    def refresh(self) -> None:
        from ..shared_lib import views as V
        try:
            conn = V.connect()
        except Exception as e:                              # noqa: BLE001
            self.md_events.set_markdown(f"_činjenični sloj nedostupan: {e}_")
            return
        try:
            for key, sql in Q.items():
                try:
                    r = V.query(sql, conn=conn)["rows"]
                    val = r[0][0] if r else None
                except V.QueryRefused:
                    val = None
                if key == "front":
                    self.vals[key].setText("—" if val is None else f"{val:.9f}")
                else:
                    self.vals[key].setText("0" if val is None else str(val))
            try:
                q = V.query("SELECT kind, title FROM pending WHERE status='open' "
                            "ORDER BY created LIMIT 8", conn=conn)["rows"]
            except V.QueryRefused:
                q = []
            self.md_queue.set_markdown(
                "\n".join(f"- **{k}** — {t}" for k, t in q) or "_ništa ne čeka_")
            ev = V.query("SELECT time, kind, actor, verdict, subject FROM events "
                         "ORDER BY id DESC LIMIT 12", conn=conn)["rows"]
            self.md_events.set_markdown("\n".join(
                f"- `{t[11:19] if t else ''}` **{k}** · {a} · {vd or ''} {s or ''}"
                for t, k, a, vd, s in ev) or "_prazno_")
        finally:
            conn.close()
