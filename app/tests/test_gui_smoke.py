"""The main window must still build headless after every phase."""
def test_main_window_builds(operator):
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from pse_r import config
    config.ensure_vault()
    from pse_r.vault import seed
    if not seed.is_seeded():
        seed.seed_all()
    from pse_r.gui.main_window import MainWindow
    w = MainWindow()
    assert "Test Operater" in w.lb_op.text()
    w.close()
