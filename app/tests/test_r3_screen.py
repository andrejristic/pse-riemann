"""Screen fitting (Andrej, 2026-10-25): measured DPI → same physical text size;
window fits the available area; remembered geometry only if it still fits."""
from PySide6.QtCore import QRect

from pse_r import screen as S


def test_physical_text_size_follows_real_dpi():
    surface = S.compute(1920, 1050, 235, 132, 1.0, 1920)        # ~207 DPI
    monitor = S.compute(1920, 1050, 480, 270, 1.0, 1920)        # this Dell, ~101 DPI
    assert surface.measured and 24 <= surface.font_pt <= 28
    assert monitor.measured and 11 <= monitor.font_pt <= 14


def test_unbelievable_or_missing_size_is_not_a_measurement():
    for mm in ((0, 0), (10, 5), (5000, 3000)):
        p = S.compute(1366, 738, *mm, 1.0, 1366)
        assert not p.measured and p.dpi is None
        assert S.MIN_PT <= p.font_pt <= S.FALLBACK_PT


def test_window_fits_available_area_and_narrow_screen_caps_font():
    p = S.compute(1024, 700, 200, 150, 1.0, 1024)
    assert p.win_w <= 1024 and p.win_h <= 700
    assert p.font_pt * 4 / 3 * 0.55 * S.CHARS_ACROSS <= 1024 + 1


def test_remembered_geometry_must_fit():
    av = QRect(0, 0, 1366, 738)
    assert S.fits(1200, 650, 50, 40, av)
    assert not S.fits(1900, 1000, 0, 0, av)                     # from the big monitor
    assert not S.fits(800, 600, 2500, 100, av)                  # off-screen (2nd monitor gone)


def test_operator_font_wins(monkeypatch):
    from pse_r import settings as ST
    monkeypatch.setattr(S, "_CURRENT", S.compute(1920, 1050, 480, 270, 1.0, 1920))
    monkeypatch.setattr(ST, "get", lambda k, d=None: 18.0 if k == "font_pt" else d)
    assert ST.base_font_pt() == 18.0
    monkeypatch.setattr(ST, "get", lambda k, d=None: 0 if k == "font_pt" else d)
    assert ST.base_font_pt() == S.current().font_pt
