"""F3 — main AI + skeptic + limiters (model-agnostic: no live model needed)."""
import threading

import pytest

from pse_r.llm import limits as L
from pse_r.llm import selection as SEL
from pse_r.llm import skeptic as SK
from pse_r.llm import gguf as G
from pse_r.shared_lib.store import store


# ---- limiters -------------------------------------------------------------- #
def test_ram_gate_and_thread_cap(monkeypatch):
    lim = L.Limits(ram_headroom_gb=2.0, ram_floor_gb=1.5, reserve_cores=1)
    monkeypatch.setattr(L, "free_ram_gb", lambda: 10.0)
    assert lim.can_load(5.5) and not lim.must_unload()
    monkeypatch.setattr(L, "free_ram_gb", lambda: 6.0)
    assert not lim.can_load(5.5)                 # 5.5 + 2 > 6
    monkeypatch.setattr(L, "free_ram_gb", lambda: 1.0)
    assert lim.must_unload()
    assert 1 <= lim.threads() <= L.cpu_count()
    assert lim.threads() == max(1, L.cpu_count() - 1)


def test_repetition_detection():
    assert L.is_looping("ista linija ovdje\n" * 5)
    assert not L.is_looping("prva\ndruga\ntreća\nčetvrta")
    assert L.is_looping("ok" + "ponavljam ovo stalno" * 6)


def test_divergence_watchdog():
    assert L.diverging([1, 2, 200], L=90)        # over ceiling
    assert L.diverging([1, 2, 3, 4], L=1000)     # three rises in a row
    assert not L.diverging([5, 1, 6, 2], L=1000)
    wd = L.Watchdog("latency", L=90)
    assert not wd.observe(10) and not wd.observe(20)
    assert wd.observe(500)                       # crossed L


def test_one_call_at_a_time():
    with L.one_at_a_time(timeout=1.0):
        got = {}

        def second():
            try:
                with L.one_at_a_time(timeout=0.2):
                    got["ok"] = True
            except TimeoutError:
                got["blocked"] = True
        t = threading.Thread(target=second)
        t.start()
        t.join()
    assert got.get("blocked") and "ok" not in got


# ---- selection policy ------------------------------------------------------ #
@pytest.fixture
def two_models(monkeypatch):
    monkeypatch.setattr(SEL, "cloud_available", lambda: ["claude", "groq"])
    monkeypatch.setattr(SEL, "gguf_available", lambda: ["gguf:deepseek.gguf"])


def test_defaults_main_strongest_skeptic_different(two_models):
    from pse_r import settings as S
    S.set_("ai_main", None)
    S.set_("ai_skeptic", None)
    assert SEL.get_main() == "claude"                 # strongest available
    sk = SEL.get_skeptic()
    assert sk != "claude" and sk.startswith("gguf:")  # prefers a local, different model
    assert SEL.skeptic_available()


def test_main_and_skeptic_cannot_be_the_same(two_models):
    SEL.set_main("claude")
    with pytest.raises(ValueError):
        SEL.set_skeptic("claude")
    SEL.set_skeptic("gguf:deepseek.gguf")
    with pytest.raises(ValueError):
        SEL.set_main("gguf:deepseek.gguf")


def test_no_models_means_no_skeptic(monkeypatch):
    monkeypatch.setattr(SEL, "cloud_available", lambda: [])
    monkeypatch.setattr(SEL, "gguf_available", lambda: [])
    from pse_r import settings as S
    S.set_("ai_main", None)
    S.set_("ai_skeptic", None)
    assert SEL.get_main() is None and not SEL.skeptic_available()


# ---- the skeptic ----------------------------------------------------------- #
def test_skeptic_parses_fixed_shape_and_queues(operator, two_models):
    fake = ('Evo prigovora:\n[{"prigovor":"Broj nije iz rada","razlog":"preprint '
            'nije recenziran","gdje":"B*","ozbiljnost":"visoka"},'
            '{"prigovor":"x","razlog":"y"}]')
    res = SK.attack("Metoda liu", "B*=0.87...", ask=lambda a, b, c: fake)
    assert res["available"] and len(res["objections"]) == 2
    o = res["objections"][0]
    assert o.ozbiljnost == "visoka" and o.gdje == "B*"
    assert res["objections"][1].ozbiljnost == "srednja"     # default filled in
    queued = store().open_items(SK.SKEPTIC_KIND)
    assert len(queued) == 2 and all("objection" in i["payload"] for i in queued)


def test_skeptic_unavailable_does_nothing(monkeypatch, operator):
    monkeypatch.setattr(SEL, "skeptic_available", lambda: False)
    before = len(store().open_items(SK.SKEPTIC_KIND))
    res = SK.attack("Metoda x", "tvrdnja", ask=lambda a, b, c: "[]")
    assert res["available"] is False and res["objections"] == []
    assert len(store().open_items(SK.SKEPTIC_KIND)) == before   # queued nothing new


# ---- GGUF backend verification (no model load) ----------------------------- #
def test_gguf_verify_rejects_missing_and_mismatched_hash(tmp_path, operator):
    b = G.GGUFBackend(str(tmp_path / "nema.gguf"))
    ok, _ = b.verify()
    assert not ok                                   # file does not exist

    f = tmp_path / "m.gguf"
    f.write_bytes(b"not a real model")
    from pse_r.shared_lib import declarations as DECL
    DECL.install_hooks()
    pid = DECL.propose({"models": {str(f): "00" * 32}}, "system")
    store().decide(pid, True)                        # declare a wrong hash
    ok, why = G.GGUFBackend(str(f)).verify()
    assert not ok and "sha256" in why
