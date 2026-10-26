"""Round 3, item 29 (step 2): the Grafovi tab — three panels, moving the view
up/down/left/right (keys, buttons, drag), zoom, "sve o tački", offers, CSV."""
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication

from pse_r.graphs import functions as F


def _tab():
    app = QApplication.instance() or QApplication([])
    from pse_r.gui.grafovi import GrafoviTab
    t = GrafoviTab()
    t.resize(1400, 800)
    t.show()
    app.processEvents()
    return app, t


def test_pan_in_all_four_directions_and_zoom():
    app, t = _tab()
    c = t.canvas
    x0, y0 = c.ax.get_xlim(), c.ax.get_ylim()
    for key, check in ((Qt.Key_Right, lambda: c.ax.get_xlim()[0] > x0[0]),
                       (Qt.Key_Left, lambda: abs(c.ax.get_xlim()[0] - x0[0]) < 1e-12),
                       (Qt.Key_Up, lambda: c.ax.get_ylim()[0] > y0[0]),
                       (Qt.Key_Down, lambda: abs(c.ax.get_ylim()[0] - y0[0]) < 1e-12)):
        c.keyPressEvent(QKeyEvent(QKeyEvent.KeyPress, key, Qt.NoModifier))
        assert check(), key
    w0 = c.ax.get_xlim()[1] - c.ax.get_xlim()[0]
    c.keyPressEvent(QKeyEvent(QKeyEvent.KeyPress, Qt.Key_Right, Qt.ShiftModifier))
    assert abs(c.ax.get_xlim()[0] - (x0[0] + 0.4 * w0)) < 1e-12           # Shift = bigger step
    c.zoom(0.5)
    assert abs((c.ax.get_xlim()[1] - c.ax.get_xlim()[0]) - w0 / 2) < 1e-12
    c.home()
    assert c.ax.get_xlim() == x0
    c.pan(0, -0.1)                                                       # the ▼ button
    assert c.ax.get_ylim()[0] < y0[0]


def test_click_shows_everything_about_the_point_and_offers():
    app, t = _tab()
    t.funcs.funcs = F.default_set()
    t.redraw()
    t._clicked("bi-B_line", 1 / 6)
    md = t.calc._info_md
    assert "7/8" in md and "RAD" in md and "izvor-openai-7-8" in md
    assert 1 <= t.calc.offers.count() <= 5                               # ≤ 4 + "više…"


def test_csv_has_the_curves_in_view(tmp_path):
    app, t = _tab()
    t.funcs.funcs = [F.builtin("B_line")]
    t.redraw()
    from pse_r.gui.grafovi import write_csv
    n = write_csv(tmp_path / "g.csv", t.canvas, t.funcs.funcs)
    rows = (tmp_path / "g.csv").read_text(encoding="utf-8").splitlines()
    assert n > 100 and rows[0] == "function,level,x,y" and "RAD" in rows[1]


def test_expand_hides_side_panels():
    app, t = _tab()
    t.toggle_expand()
    assert not t.funcs.isVisible() and not t.calc.isVisible()
    t.toggle_expand()
    assert t.funcs.isVisible() and t.calc.isVisible()


def test_each_of_the_three_panels_can_fill_the_tab():
    app, t = _tab()
    for name, btn in (("funcs", t.funcs.b_expand), ("graph", t.b_expand_graph),
                      ("calc", t.calc.b_expand)):
        btn.click()
        app.processEvents()
        assert [k for k, w in t._panels.items() if w.isVisible()] == [name]
        assert btn.text() == "⤡"
        btn.click()
        app.processEvents()
        assert all(w.isVisible() for w in t._panels.values())


def test_unsafe_function_is_refused_before_drawing():
    import pytest
    from pse_r.graphs import fexpr as FX
    with pytest.raises(FX.FExprError):
        F.validate(F.Function("x", "x", "real", "__import__('os').system('ls')"))
    app, t = _tab()
    t.funcs.funcs = [F.Function("u", "u", "real", "sin(30*x)/x", domain=[0, 1])]
    t.redraw()                                                           # NaN at 0 is a gap, not a crash
    xs, ys = t.canvas._lines["u"]
    assert np.isfinite(ys).sum() > 100
