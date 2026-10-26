"""
The Grafovi tab (round 3, item 29) — modelled on "Calculus Tools" (Andrej): three
parts side by side on a computer screen,

    Funkcije      the functions (unlimited, each its own colour) + parameter sliders
    Grafovi       the plot: dark, zoom (wheel, + / −), move up/down/left/right
                  (drag, arrow keys — Shift = bigger step, ◀ ▲ ▼ ▶), ⌂ = reset;
                  the mouse shows everything known about the point under it
    Kalkulacije   "sve o tački" for the clicked point + calculations on demand:
                  cheap ones at once, expensive ones only offered with an estimate,
                  run in the background with "Prekini"

"⤢" spreads the plot over the whole tab (and back). Every plot is stamped with the
levels of what it shows (RAD / NAŠE-NERECENZIRANO / KORISNIK). Export: PNG, SVG, CSV.
The guide is docs/VODIC-GRAFOVI-SR.md ("?").
"""
from __future__ import annotations

import csv
import threading
from pathlib import Path
from typing import Optional

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QCheckBox, QColorDialog, QComboBox, QDialog, QDialogButtonBox,
                               QFileDialog, QFormLayout, QGridLayout, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QMenu, QMessageBox, QSlider,
                               QSplitter, QVBoxLayout, QWidget)

from ..graphs import compute as C
from ..graphs import fexpr as FX
from ..graphs import functions as F
from ..i18n import tr
from .widgets import MarkdownView, button, flow_row

BG, AX, GRID, TXT, MUTED = "#12151d", "#171b25", "#262d3a", "#e9ecf3", "#9aa4b5"
SLIDERS = {  # name: (label, lo, hi)
    "l": ("ℓ", 0.0, 0.3), "b": ("b", 0.0, 0.3), "k": ("κ", 0.5, 1.0), "t": ("t", 0.0, 1.0),
    "w": ("w", 0.0, 0.25), "d": ("d", 1.0, 4.0), "low": ("niska strana", 0.0, 0.3),
    "delta": ("Δ", 0.0, 0.3)}
PAN_STEP, PAN_BIG = 0.10, 0.40


def _base_pt() -> float:
    from .widgets import _BASE_PT
    return _BASE_PT[0]


def _samples() -> int:
    try:
        from .. import machine as MC
        return 300 if MC.profile().key == "acer" else 600
    except Exception:                                   # noqa: BLE001
        return 500


class _Bridge(QObject):
    """Worker threads → GUI thread."""
    job_done = Signal(str, dict)
    coarse_done = Signal()


# --------------------------------------------------------------------------- #
# the plot
# --------------------------------------------------------------------------- #
class GraphCanvas(FigureCanvasQTAgg):
    hovered = Signal(str)
    clicked = Signal(str, float)          # function id, x
    card = Signal(str)

    def __init__(self, parent=None):
        self.fig = Figure(facecolor=BG, layout="constrained")   # tick labels never clipped
        super().__init__(self.fig)
        self.setParent(parent)
        self.setFocusPolicy(Qt.StrongFocus)
        self.ax = self.fig.add_subplot(111)
        self.funcs: list = []
        self.params: dict = dict(F.PARAMS)
        self.show_targets = True
        self.show_walls = True
        self.home_view = ((0.0, 0.3), (0.80, 0.95))
        self._drag = None
        self._moved = False
        self._lines: dict = {}            # fid -> (xs, ys)
        self._coarse: dict = {}           # (fid, params) -> (xs, ys) for expensive builtins
        self._pending: set = set()
        self.bridge = _Bridge()
        self.bridge.coarse_done.connect(self.redraw)
        self.ax.set_xlim(*self.home_view[0])
        self.ax.set_ylim(*self.home_view[1])
        self.mpl_connect("scroll_event", self._on_scroll)
        self.mpl_connect("button_press_event", self._on_press)
        self.mpl_connect("button_release_event", self._on_release)
        self.mpl_connect("motion_notify_event", self._on_motion)
        self._annot = None

    # ---- navigation -------------------------------------------------- #
    def pan(self, fx: float, fy: float) -> None:
        """Move the view by a fraction of its width/height (+x right, +y up)."""
        x0, x1 = self.ax.get_xlim()
        y0, y1 = self.ax.get_ylim()
        dx, dy = (x1 - x0) * fx, (y1 - y0) * fy
        self.ax.set_xlim(x0 + dx, x1 + dx)
        self.ax.set_ylim(y0 + dy, y1 + dy)
        self.redraw()

    def zoom(self, factor: float, cx: Optional[float] = None, cy: Optional[float] = None) -> None:
        x0, x1 = self.ax.get_xlim()
        y0, y1 = self.ax.get_ylim()
        cx = (x0 + x1) / 2 if cx is None else cx
        cy = (y0 + y1) / 2 if cy is None else cy
        self.ax.set_xlim(cx + (x0 - cx) * factor, cx + (x1 - cx) * factor)
        self.ax.set_ylim(cy + (y0 - cy) * factor, cy + (y1 - cy) * factor)
        self.redraw()

    def home(self) -> None:
        self.ax.set_xlim(*self.home_view[0])
        self.ax.set_ylim(*self.home_view[1])
        self.redraw()

    def keyPressEvent(self, ev):
        big = PAN_BIG if ev.modifiers() & Qt.ShiftModifier else PAN_STEP
        k = ev.key()
        moves = {Qt.Key_Left: (-big, 0), Qt.Key_Right: (big, 0),
                 Qt.Key_Up: (0, big), Qt.Key_Down: (0, -big)}
        if k in moves:
            self.pan(*moves[k])
        elif k in (Qt.Key_Plus, Qt.Key_Equal):
            self.zoom(0.8)
        elif k == Qt.Key_Minus:
            self.zoom(1.25)
        elif k == Qt.Key_Home:
            self.home()
        else:
            super().keyPressEvent(ev)

    def _on_scroll(self, ev):
        if ev.xdata is None:
            return
        self.zoom(0.85 if ev.button == "up" else 1 / 0.85, ev.xdata, ev.ydata)

    def _on_press(self, ev):
        self.setFocus()
        if ev.inaxes is not self.ax or ev.button != 1:
            return
        if ev.dblclick:
            hit = self.nearest(ev)
            if hit and hit[0].card:
                self.card.emit(hit[0].card)
            return
        self._drag = (ev.x, ev.y, self.ax.get_xlim(), self.ax.get_ylim())
        self._moved = False

    def _on_release(self, ev):
        drag, self._drag = self._drag, None
        if drag is None or self._moved:
            return
        hit = self.nearest(ev)
        if hit:
            self.clicked.emit(hit[0].id, hit[1])

    def _on_motion(self, ev):
        if self._drag is not None and ev.x is not None:
            x0p, y0p, (xa, xb), (ya, yb) = self._drag
            if abs(ev.x - x0p) + abs(ev.y - y0p) > 3:
                self._moved = True
            w, h = self.ax.bbox.width, self.ax.bbox.height
            dx = (ev.x - x0p) / w * (xb - xa)
            dy = (ev.y - y0p) / h * (yb - ya)
            self.ax.set_xlim(xa - dx, xb - dx)
            self.ax.set_ylim(ya - dy, yb - dy)
            self.redraw(fast=True)
            return
        if ev.inaxes is not self.ax:
            return
        hit = self.nearest(ev)
        if hit is None:
            self.hovered.emit(tr("x = {0:.6g}, y = {1:.6g}").format(ev.xdata, ev.ydata))
            return
        f, x, y = hit
        tgt = C.nearest_target(y)
        self.hovered.emit(tr("{0} · ({1:.9g}, {2:.9g}) · {3} · najbliži cilj {4} (Δ {5:.3g}) — klik = sve o tački")
                          .format(f.label, x, y, f.level, tgt[0], tgt[2]))

    def nearest(self, ev, px: float = 12.0):
        """The function curve nearest to the mouse (within px pixels): (f, x, y)."""
        if ev.xdata is None:
            return None
        best = None
        inv = self.ax.transData
        for f in self.funcs:
            if f.id not in self._lines:
                continue
            xs, ys = self._lines[f.id]
            if len(xs) == 0:
                continue
            i = int(np.clip(np.searchsorted(xs, ev.xdata), 1, len(xs) - 1))
            for j in (i - 1, i):
                if not np.isfinite(ys[j]):
                    continue
                sx, sy = inv.transform((xs[j], ys[j]))
                d = float(np.hypot(sx - ev.x, sy - ev.y))
                if d <= px and (best is None or d < best[0]):
                    best = (d, f, float(xs[j]), float(ys[j]))
        return None if best is None else best[1:]

    # ---- drawing ----------------------------------------------------- #
    def _style(self):
        fs = max(7.0, _base_pt() * 0.62)
        ax = self.ax
        ax.set_facecolor(AX)
        for s in ax.spines.values():
            s.set_color(GRID)
        ax.tick_params(colors=MUTED, labelsize=fs)
        ax.grid(True, color=GRID, linewidth=0.6, alpha=0.9)
        return fs

    def _sample(self, f: F.Function, x0: float, x1: float):
        # built-ins are code with a domain; typed functions are drawn over the whole view
        lo, hi = (max(x0, f.domain[0]), min(x1, f.domain[1])) if f.kind == "builtin" else (x0, x1)
        if hi <= lo:
            return np.array([]), np.array([])
        n = _samples()
        cost = F.eval_cost(f, self.params) * n
        if f.kind == "builtin" and cost > C.CHEAP_S:
            key = (f.id, tuple(sorted(self.params.items())))
            if key in self._coarse:
                return self._coarse[key]
            if key not in self._pending:
                self._pending.add(key)
                k = F.BUILTINS[f.builtin].get("coarse", 9)
                dom = tuple(f.domain)

                def work():
                    xs = np.linspace(dom[0], dom[1], k)
                    try:
                        ys = np.asarray(F.numeric(f, self.params)(xs), float)
                    except Exception:                   # noqa: BLE001
                        ys = np.full(k, np.nan)
                    self._coarse[key] = (xs, ys)
                    self._pending.discard(key)
                    self.bridge.coarse_done.emit()
                threading.Thread(target=work, name="grafovi-coarse", daemon=True).start()
            return np.array([]), np.array([])
        xs = np.linspace(lo, hi, n)
        try:
            ys = np.asarray(F.numeric(f, self.params)(xs), dtype=float)
        except Exception:                               # noqa: BLE001
            ys = np.full(n, np.nan)
        return xs, ys

    def redraw(self, fast: bool = False):
        xl, yl = self.ax.get_xlim(), self.ax.get_ylim()
        self.ax.clear()
        fs = self._style()
        self.ax.set_xlim(*xl)
        self.ax.set_ylim(*yl)
        self._lines.clear()
        levels, waiting = set(), []
        for f in self.funcs:
            if not f.visible or f.kind not in ("real", "builtin"):
                continue
            xs, ys = self._sample(f, *xl)
            if len(xs) == 0:
                if any(k[0] == f.id for k in self._pending):
                    waiting.append(f.label)
                continue
            self._lines[f.id] = (xs, ys)
            self.ax.plot(xs, ys, color=f.color, linewidth=1.8, label=f.label,
                         marker="o" if len(xs) < 30 else None, markersize=3)
            levels.add(f.level)
        if self.show_targets:
            for name, v in F.TARGETS.items():
                if yl[0] <= v <= yl[1]:
                    self.ax.axhline(v, color="#6b7585", linewidth=0.8, linestyle="--")
                    self.ax.text(xl[1], v, f" {name}", color=MUTED, fontsize=fs * 0.9,
                                 va="center", ha="right")
        if self.show_walls:
            for name, v in C.WALL_LINES["B"].items():
                if yl[0] <= v <= yl[1]:
                    self.ax.axhline(v, color="#f49090", linewidth=0.9, linestyle=":")
            for name, v in C.WALL_LINES["x"].items():
                if xl[0] <= v <= xl[1]:
                    self.ax.axvline(v, color="#f49090", linewidth=0.9, linestyle=":")
                    self.ax.text(v, yl[1], f" {name}", color="#f49090", fontsize=fs * 0.8,
                                 va="top", rotation=90)
        if self._lines:
            leg = self.ax.legend(loc="lower left", fontsize=fs * 0.85, facecolor=AX,
                                 edgecolor=GRID, labelcolor=TXT)
            leg.set_draggable(True)
        stamp = " · ".join(sorted(levels)) or "—"
        self.ax.set_title(tr("nivo: {0}").format(stamp) + (tr("   ·   računam: {0}…").format(", ".join(waiting)) if waiting else ""),
                          color=MUTED, fontsize=fs, loc="right")
        self.draw_idle()

    def visible_data(self) -> dict:
        return {fid: (xs.tolist(), ys.tolist()) for fid, (xs, ys) in self._lines.items()}


# --------------------------------------------------------------------------- #
# Funkcije panel
# --------------------------------------------------------------------------- #
class FunctionDialog(QDialog):
    def __init__(self, f: Optional[F.Function] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Funkcija"))
        form = QFormLayout(self)
        self.kind = QComboBox()
        for k, txt in (("real", tr("realna  y = f(x)")), ("complex", tr("kompleksna  w = f(s)")),
                       ("surface", tr("površ  z = f(x, y)")), ("parametric", tr("parametarska  x(u); y(u)")),
                       ("polar", tr("polarna  r = f(th)"))):
            self.kind.addItem(txt, k)
        self.expr = QLineEdit()
        self.expr.setPlaceholderText(tr("npr. 11/12 - x/4   ·   x**3 - 2   ·   zeta(s)   ·   cos(u); sin(u)"))
        self.label = QLineEdit()
        self.lo, self.hi = QLineEdit("0"), QLineEdit("1")
        form.addRow(tr("vrsta:"), self.kind)
        form.addRow(tr("izraz:"), self.expr)
        form.addRow(tr("ime:"), self.label)
        form.addRow(tr("domen od:"), self.lo)
        form.addRow(tr("domen do:"), self.hi)
        form.addRow(QLabel(tr("Dozvoljeno: + − × ÷ **, sin cos tan exp log sqrt abs atan … zeta Z gamma re im arg; "
                              "klizači: l b k t w d low delta. Ništa drugo (provjera prije prevođenja).")))
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self._ok)
        bb.rejected.connect(self.reject)
        form.addRow(bb)
        self.result_f: Optional[F.Function] = None
        self._orig = f
        if f is not None:
            self.kind.setCurrentIndex(max(0, self.kind.findData(f.kind)))
            self.expr.setText(f.expr)
            self.label.setText(f.label)
            self.lo.setText(f"{f.domain[0]:g}")
            self.hi.setText(f"{f.domain[1]:g}")

    def _ok(self):
        import time as _t
        try:
            dom = [float(self.lo.text()), float(self.hi.text())]
            if dom[1] <= dom[0]:
                raise ValueError(tr("domen: „do“ mora biti veće od „od“"))
            f = F.Function(id=self._orig.id if self._orig else f"f-{int(_t.time() * 1000)}",
                           label=self.label.text().strip() or self.expr.text().strip(),
                           kind=self.kind.currentData(), expr=self.expr.text().strip(),
                           color=self._orig.color if self._orig else "#ffb74d",
                           level=F.USER, domain=dom)
            F.validate(f)
        except (FX.FExprError, ValueError) as e:
            QMessageBox.warning(self, tr("Funkcija"), str(e))
            return
        self.result_f = f
        self.accept()


def _header(title: str, expand_signal) -> tuple:
    """Panel title + its own ⤢ button (each of the three panels can fill the tab)."""
    b = button("⤢", lambda: expand_signal.emit())
    b.setToolTip(tr("raširi ovaj panel preko cijelog taba (ponovo = vrati)"))
    return flow_row(QLabel(title), b), b


class FunctionsPanel(QWidget):
    changed = Signal()
    expand = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        row, self.b_expand = _header(tr("<b>Funkcije</b>"), self.expand)
        v.addWidget(row)
        self.list = QListWidget()
        self.list.itemChanged.connect(self._toggled)
        self.list.itemDoubleClicked.connect(lambda _it: self._edit())
        v.addWidget(self.list, 1)
        self.b_builtin = button(tr("+ ugrađena"), self._builtin_menu)
        v.addWidget(flow_row(button(tr("+ funkcija"), self._add), self.b_builtin,
                             button(tr("Uredi"), self._edit), button(tr("Boja"), self._color),
                             button(tr("Ukloni"), self._remove)))
        v.addWidget(QLabel(tr("<b>Parametri</b> (klizači)")))
        grid = QGridLayout()
        self.sliders: dict = {}
        self.vals: dict = {}
        for r, (name, (lab, lo, hi)) in enumerate(SLIDERS.items()):
            s = QSlider(Qt.Horizontal)
            s.setRange(0, 1000)
            s.setValue(int(round((F.PARAMS[name] - lo) / (hi - lo) * 1000)))
            val = QLabel("")
            s.valueChanged.connect(lambda _v, n=name: self._slid(n))
            grid.addWidget(QLabel(tr(lab)), r, 0)
            grid.addWidget(s, r, 1)
            grid.addWidget(val, r, 2)
            self.sliders[name], self.vals[name] = s, val
        grid.setColumnStretch(1, 1)
        for s in self.sliders.values():
            s.setMinimumWidth(40)
        v.addLayout(grid)
        self.sigma = QLabel("")                          # σ* = 11/16 + niska strana (own line)
        v.addWidget(self.sigma)
        self.funcs = F.load()
        self.params = dict(F.PARAMS)
        for n in SLIDERS:
            self._slid(n, emit=False)
        self._slid("low", emit=False)
        self.refresh()

    def value(self, name: str) -> float:
        _lab, lo, hi = SLIDERS[name]
        return lo + (hi - lo) * self.sliders[name].value() / 1000

    def _slid(self, name: str, emit: bool = True):
        self.params[name] = self.value(name)
        self.vals[name].setText(f"{self.params[name]:.4f}")
        if name == "low" and hasattr(self, "sigma"):
            self.sigma.setText(tr("  → σ* = {0:.4f}").format(11 / 16 + self.params[name]))
        if emit:
            self.changed.emit()

    def refresh(self):
        self.list.blockSignals(True)
        cur = self.current_id()
        self.list.clear()
        for f in self.funcs:
            it = QListWidgetItem(f"{f.label}   [{f.level}]")
            it.setData(Qt.UserRole, f.id)
            it.setForeground(QColor(f.color))
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked if f.visible else Qt.Unchecked)
            it.setToolTip(f.meaning or f.expr)
            self.list.addItem(it)
            if f.id == cur:
                self.list.setCurrentItem(it)
        self.list.blockSignals(False)

    def current_id(self) -> Optional[str]:
        it = self.list.currentItem()
        return it.data(Qt.UserRole) if it else None

    def _find(self, fid):
        return next((f for f in self.funcs if f.id == fid), None)

    def _save(self):
        F.save(self.funcs)
        self.refresh()
        self.changed.emit()

    def _toggled(self, it):
        f = self._find(it.data(Qt.UserRole))
        if f:
            f.visible = it.checkState() == Qt.Checked
            F.save(self.funcs)
            self.changed.emit()

    def _add(self):
        d = FunctionDialog(parent=self)
        if d.exec() and d.result_f:
            d.result_f.color = F.next_color(self.funcs)
            self.funcs.append(d.result_f)
            self._save()

    def _builtin_menu(self):
        m = QMenu(self)
        for key, b in F.BUILTINS.items():
            m.addAction(f"{b['label']}   [{b['level']}]", lambda k=key: self._add_builtin(k))
        m.exec(self.b_builtin.mapToGlobal(self.b_builtin.rect().bottomLeft()))

    def _add_builtin(self, key):
        if any(f.builtin == key for f in self.funcs):
            return
        self.funcs.append(F.builtin(key, F.next_color(self.funcs)))
        self._save()

    def _edit(self):
        f = self._find(self.current_id())
        if f is None or f.kind == "builtin":
            return
        d = FunctionDialog(f, self)
        if d.exec() and d.result_f:
            self.funcs[self.funcs.index(f)] = d.result_f
            self._save()

    def _color(self):
        f = self._find(self.current_id())
        if f is None:
            return
        c = QColorDialog.getColor(QColor(f.color), self)
        if c.isValid():
            f.color = c.name()
            self._save()

    def _remove(self):
        f = self._find(self.current_id())
        if f is not None:
            self.funcs.remove(f)
            self._save()


# --------------------------------------------------------------------------- #
# Kalkulacije panel
# --------------------------------------------------------------------------- #
def info_md(info: dict) -> str:
    out = [tr("### Sve o tački"), "",
           f"**{info['function']}** · {info['level']}" + (f" · [[{info['card']}]]" if info.get("card") else ""),
           "", f"x = `{info['x']:.12g}`, y = `{info['y']:.12g}`" if F.is_finite(info["y"]) else f"x = `{info['x']:.12g}`"]
    if info.get("meaning"):
        out += ["", tr("**Značenje:** {0}").format(info["meaning"])]
    if info.get("flags"):
        out += ["", tr("**Tačka je:** {0}").format("; ".join(info["flags"]))]
    if info.get("dydx") is not None:
        out += ["", f"f′ = `{info['dydx']:.9g}`"]
    if info.get("targets"):
        out += ["", tr("**Udaljenost do ciljeva:** ") + " · ".join(
            f"{k}: {v:+.6g}" for k, v in info["targets"].items())]
    ps = info.get("params", {})
    out += ["", tr("**Parametri:** ") + ", ".join(f"{k}={v:.4g}" for k, v in ps.items())]
    return "\n".join(out)


def result_md(title: str, res: dict) -> str:
    st = res.get("status", "")
    lines = [f"#### {title} — {st}"]
    for k, v in res.items():
        if k in ("status",):
            continue
        if isinstance(v, float):
            v = f"{v:.12g}"
        elif isinstance(v, (dict, list)):
            import json
            v = "`" + json.dumps(v, ensure_ascii=False, default=str)[:600] + "`"
        lines.append(f"- **{k}**: {v}")
    lines.append(tr("_oznaka: NAŠE-NERECENZIRANO — računao Python, deterministički_"))
    return "\n".join(lines)


class CalcPanel(QWidget):
    open_card = Signal(str)
    expand = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        row, self.b_expand = _header(tr("<b>Kalkulacije</b>"), self.expand)
        v.addWidget(row)
        self.view = MarkdownView()
        if hasattr(self.view, "anchorClicked"):
            self.view.anchorClicked.connect(lambda url: self.open_card.emit(url.toString().split("/")[-1]))
        v.addWidget(self.view, 1)
        # offers as a wrapping list (long sentences must not widen the panel)
        self.offers = QListWidget()
        self.offers.setWordWrap(True)
        self.offers.setMaximumHeight(int(_base_pt() * 9))
        self.offers.itemActivated.connect(self._offer_clicked)
        self.offers.itemClicked.connect(self._offer_clicked)
        v.addWidget(self.offers)
        self.b_cancel = button(tr("Prekini"), lambda: C.JOBS.cancel_all(), kind="no")
        self.status = QLabel("")
        self.status.setWordWrap(True)
        v.addWidget(flow_row(self.status, self.b_cancel))
        self.bridge = _Bridge()
        self.bridge.job_done.connect(self._job_done)
        self._ctx = None
        self._results: list = []
        self.view.set_markdown(tr("_Klikni na krivu: ovdje se pojavi sve što se zna o toj tački i ponude računa._"))

    def show_point(self, f: F.Function, x: float, funcs: list, params: dict, yspan: float):
        info = C.point_info(f, x, funcs, params, yspan)
        self._ctx = (f, x, funcs, params)
        self._results = []
        self._info_md = info_md(info)
        self.view.set_markdown(self._info_md)
        self.offers.clear()
        offs = C.offers(f, info, funcs)
        main = [o for o in offs if not o.get("more")]
        more = [o for o in offs if o.get("more")]
        self._more = more
        for o in main:
            it = QListWidgetItem("▸ " + self._offer_text(o))
            it.setData(Qt.UserRole, o)
            it.setToolTip(o.get("why", ""))
            self.offers.addItem(it)
        if more:
            it = QListWidgetItem(tr("▸ više… ({0})").format(len(more)))
            it.setData(Qt.UserRole, {"key": "__more__"})
            self.offers.addItem(it)
        # cheap ones right away (tangent is always cheap for typed functions)
        for o in main:
            if not o["ask"] and o["key"] in ("tangent",):
                self._run(o)

    def _offer_text(self, o) -> str:
        est = o["est_s"]
        dur = tr("odmah") if not o["ask"] else (tr("~{0:.0f} s").format(est) if est < 120 else tr("~{0:.0f} min").format(est / 60))
        return tr("Želiš li da izračunam: {0}? ({1})").format(tr(o["title"]).format(*o.get("args", [])), dur) if o["ask"] \
            else tr("{0} ({1})").format(tr(o["title"]).format(*o.get("args", [])), dur)

    def _offer_clicked(self, it):
        o = it.data(Qt.UserRole)
        if not o:
            return
        if o.get("key") == "__more__":
            m = QMenu(self)
            for oo in self._more:
                m.addAction(self._offer_text(oo), lambda x=oo: self._ask(x))
            m.exec(self.offers.mapToGlobal(self.offers.visualItemRect(it).bottomLeft()))
            return
        self._ask(o)

    def _ask(self, o):
        if o["ask"]:
            r = QMessageBox.question(self, tr("Kalkulacije"), self._offer_text(o) + "\n\n" +
                                     tr("Računa se u pozadini; možeš prekinuti dugmetom „Prekini“."))
            if r != QMessageBox.Yes:
                return
        self._run(o)

    def _run(self, o):
        if not self._ctx:
            return
        f, x, funcs, params = self._ctx
        self.status.setText(tr("računam: {0}…").format(tr(o["title"]).format(*o.get("args", []))))
        C.JOBS.submit(o["key"], f, x, funcs, params,
                      done=lambda jid, res, t=tr(o["title"]).format(*o.get("args", [])): self.bridge.job_done.emit(t, dict(res)))

    def _job_done(self, title: str, res: dict):
        self.status.setText(tr("{0}: {1}").format(title, res.get("status", "")))
        self._results.append(result_md(title, res))
        self.view.set_markdown(self._info_md + "\n\n" + "\n\n".join(self._results))


# --------------------------------------------------------------------------- #
# the tab
# --------------------------------------------------------------------------- #
class GrafoviTab(QWidget):
    open_card = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        v = QVBoxLayout(self)
        self.mode = QComboBox()
        self.mode.addItem(tr("Kartezijanski"), "cartesian")
        self.cb_t = QCheckBox(tr("ciljevi"))
        self.cb_t.setChecked(True)
        self.cb_w = QCheckBox(tr("zidovi"))
        self.cb_w.setChecked(True)
        self.b_expand = button(tr("⤢ raširi"), self.toggle_expand)
        v.addWidget(flow_row(
            QLabel(tr("<b>Grafovi</b>")), QLabel(tr("prikaz:")), self.mode, self.cb_t, self.cb_w,
            button("◀", lambda: self.canvas.pan(-PAN_STEP, 0)), button("▲", lambda: self.canvas.pan(0, PAN_STEP)),
            button("▼", lambda: self.canvas.pan(0, -PAN_STEP)), button("▶", lambda: self.canvas.pan(PAN_STEP, 0)),
            button("+", lambda: self.canvas.zoom(0.8)), button("−", lambda: self.canvas.zoom(1.25)),
            button("⌂", lambda: self.canvas.home()),
            button(tr("PNG"), lambda: self.export("png")), button(tr("SVG"), lambda: self.export("svg")),
            button(tr("CSV"), self.export_csv), self.b_expand, button("?", self.guide)))
        self.split = QSplitter(Qt.Horizontal)
        self.split.setObjectName("grafovi")
        self.funcs = FunctionsPanel()
        self.canvas = GraphCanvas()
        mid = QWidget()
        mv = QVBoxLayout(mid)
        mv.setContentsMargins(0, 0, 0, 0)
        self.b_expand_graph = button("⤢", lambda: self.expand_panel("graph"))
        self.b_expand_graph.setToolTip(tr("raširi ovaj panel preko cijelog taba (ponovo = vrati)"))
        mv.addWidget(flow_row(QLabel(tr("<b>Graf</b>")), self.b_expand_graph))
        mv.addWidget(self.canvas, 1)
        self.hover = QLabel("")
        self.hover.setWordWrap(True)
        self.hover.setStyleSheet(f"color:{MUTED};")
        mv.addWidget(self.hover)
        self.calc = CalcPanel()
        from .widgets import scroll_wrap
        # side panels scroll instead of forcing the plot narrow (26 pt on the Surface)
        self._side = (scroll_wrap(self.funcs), scroll_wrap(self.calc))
        for w in (self._side[0], mid, self._side[1]):
            self.split.addWidget(w)
        self._panels = {"funcs": self._side[0], "graph": mid, "calc": self._side[1]}
        self._btns = {"funcs": self.funcs.b_expand, "graph": self.b_expand_graph,
                      "calc": self.calc.b_expand}
        self.funcs.expand.connect(lambda: self.expand_panel("funcs"))
        self.calc.expand.connect(lambda: self.expand_panel("calc"))
        self.split.setStretchFactor(0, 2)
        self.split.setStretchFactor(1, 5)
        self.split.setStretchFactor(2, 3)
        v.addWidget(self.split, 1)
        self.funcs.changed.connect(self.redraw)
        self.cb_t.toggled.connect(self.redraw)
        self.cb_w.toggled.connect(self.redraw)
        self.canvas.hovered.connect(self.hover.setText)
        self.canvas.clicked.connect(self._clicked)
        self.canvas.card.connect(self.open_card.emit)
        self.calc.open_card.connect(self.open_card.emit)
        self._expanded = None
        self._sized = False
        self.setStyleSheet(
            "QSlider::groove:horizontal { height:6px; background:#262d3a; border-radius:3px; }"
            "QSlider::sub-page:horizontal { background:#ffc257; border-radius:3px; }"
            "QSlider::handle:horizontal { background:#e9ecf3; width:14px; margin:-5px 0; border-radius:7px; }")
        self.redraw()

    def showEvent(self, ev):
        super().showEvent(ev)
        if not self._sized:                     # the plot gets the most room
            self._sized = True
            w = max(600, self.split.width())
            self.split.setSizes([int(w * 0.22), int(w * 0.50), int(w * 0.28)])

    def redraw(self):
        self.canvas.funcs = self.funcs.funcs
        self.canvas.params = dict(self.funcs.params)
        self.canvas.show_targets = self.cb_t.isChecked()
        self.canvas.show_walls = self.cb_w.isChecked()
        self.canvas.redraw()

    def _clicked(self, fid: str, x: float):
        f = next((g for g in self.funcs.funcs if g.id == fid), None)
        if f is None:
            return
        y0, y1 = self.canvas.ax.get_ylim()
        self.calc.show_point(f, x, self.funcs.funcs, dict(self.funcs.params), y1 - y0)

    def toggle_expand(self):
        """The toolbar "⤢ raširi" = the plot panel's own ⤢."""
        self.expand_panel("graph")

    def expand_panel(self, name: str):
        """Fill the tab with one panel (Funkcije / Graf / Kalkulacije); again = all three."""
        self._expanded = None if self._expanded == name else name
        for key, w in self._panels.items():
            w.setVisible(self._expanded in (None, key))
            self._btns[key].setText("⤡" if self._expanded == key else "⤢")
        self.funcs.setVisible(self._expanded in (None, "funcs"))
        self.calc.setVisible(self._expanded in (None, "calc"))
        self.b_expand.setText(tr("⤡ vrati") if self._expanded == "graph" else tr("⤢ raširi"))

    def export(self, fmt: str):
        p, _ = QFileDialog.getSaveFileName(self, tr("Izvezi graf"), f"graf.{fmt}", f"*.{fmt}")
        if p:
            self.canvas.fig.savefig(p, format=fmt, facecolor=BG)

    def export_csv(self):
        p, _ = QFileDialog.getSaveFileName(self, tr("Izvezi podatke"), "graf.csv", "*.csv")
        if not p:
            return
        write_csv(Path(p), self.canvas, self.funcs.funcs)

    def guide(self):
        from .. import config
        from ..i18n import lang
        name = "VODIC-GRAFOVI-EN.md" if lang() == "en" else "VODIC-GRAFOVI-SR.md"
        for base in (config.APP_ROOT.parent / "docs", config.APP_ROOT / "docs",
                     Path("/usr/share/doc/pse-riemann")):
            q = base / name
            if q.exists():
                d = QDialog(self)
                d.setWindowTitle(tr("Vodič: Grafovi"))
                lay = QVBoxLayout(d)
                mv = MarkdownView()
                mv.set_markdown(q.read_text(encoding="utf-8"))
                lay.addWidget(mv)
                from .. import screen as SCR
                SCR.fit(d, 900, 800)
                d.exec()
                return
        QMessageBox.information(self, tr("Vodič"), tr("Vodič nije pronađen ({0}).").format(name))


def write_csv(path: Path, canvas: GraphCanvas, funcs: list) -> int:
    """The sampled data of every curve in view: function, level, x, y."""
    by_id = {f.id: f for f in funcs}
    n = 0
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["function", "level", "x", "y"])
        for fid, (xs, ys) in canvas.visible_data().items():
            f = by_id.get(fid)
            for x, y in zip(xs, ys):
                w.writerow([f.label if f else fid, f.level if f else "", repr(x), repr(y)])
                n += 1
    return n
