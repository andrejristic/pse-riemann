"""Live test rc3: (1) choosing the skeptic crashed the app — the OpenRouter model
list was put into the combo from the worker thread; (2) the installed selftest
wrote into the real vault."""
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest


@pytest.fixture
def app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_model_list_lands_in_gui_thread(app, monkeypatch):
    from PySide6.QtCore import QThread
    from pse_r.gui import setup as SU
    from pse_r.llm import backend as B
    names = [f"vendor/model-{i}" for i in range(400)]
    seen = []

    def fake_list(provider):
        time.sleep(0.05)
        return names
    monkeypatch.setattr(B, "list_models", fake_list)
    mp = SU.ModelPicker(skeptic=True)
    orig = mp.model.addItems
    monkeypatch.setattr(mp.model, "addItems",
                        lambda xs: (seen.append(QThread.currentThread() is app.thread()), orig(xs)))
    mp.lst.setCurrentRow([mp.lst.item(i).data(256) for i in range(mp.lst.count())].index("openrouter"))
    end = time.time() + 5
    while time.time() < end and mp._jobs:       # a load the row change may have started
        app.processEvents()
        time.sleep(0.02)
    seen.clear()
    mp._load_models()
    end = time.time() + 5
    while time.time() < end and (not seen or mp._jobs):
        app.processEvents()
        time.sleep(0.02)
    assert seen and all(seen)                   # filled from the GUI thread
    assert mp.model.count() == 400
    assert not mp._jobs                         # thread finished and released


def test_selftest_never_touches_the_given_vault(tmp_path):
    vault = tmp_path / "real-vault"
    env = dict(os.environ, PSE_RIEMANN_VAULT=str(vault), XDG_CONFIG_HOME=str(tmp_path / "cfg"),
               QT_QPA_PLATFORM="offscreen")
    env.pop("PSE_RIEMANN_SELFTEST_VAULT", None)
    app_dir = Path(__file__).resolve().parents[1]
    r = subprocess.run([sys.executable, str(app_dir / "main.py"), "--selftest"], env=env,
                       capture_output=True, text=True, timeout=600)
    assert "SVE PROLAZI" in r.stdout, r.stdout[-2000:] + r.stderr[-2000:]
    assert not vault.exists()                   # nothing written to the operator's vault
    assert not (tmp_path / "cfg" / "pse-riemann").exists()
