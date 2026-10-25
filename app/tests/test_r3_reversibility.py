"""Round 3, item 5 (Svarog S4): every action declares reversibility;
undeclared = irreversible; only reversible actions run without the operator."""
import pytest

from pse_r.core import actions as A
from pse_r.guardian import harms as HRM
from pse_r.guardian.healing import Healer, TIER2
from pse_r.shared_lib.store import store


def test_undeclared_is_irreversible_and_refused():
    s = A.spec("nešto-što-niko-nije-deklarisao")
    assert not s.declared and not s.reversible and not s.auto and s.tier == 2
    with pytest.raises(A.NotAllowed):
        A.require_auto("nešto-što-niko-nije-deklarisao")


def test_reversible_needs_an_undo():
    with pytest.raises(ValueError):
        A.declare("r3-test-bez-undo", reversible=True)


def test_human_tier_is_derived_from_declarations():
    for name in ("fisija", "zamjena", "smrt", "ponovni-prijem-modela",
                 "vraćanje-fajlova-operatera"):
        assert name in TIER2 and not A.may_auto(name)
    for name in ("contain", "boundary-reset", "vraćanje-fajlova-iz-pečata",
                 "označi-REFUTED/SUSPECT", "model.unload", "guard.pause"):
        assert A.may_auto(name) and A.spec(name).undo


def test_healer_queues_every_non_reversible_step(operator, monkeypatch):
    # a ladder step nobody declared must go to the human, not run
    monkeypatch.setattr(Healer, "_ladder",
                        staticmethod(lambda f: [("boundary-reset", 1),
                                                ("nova-nedeklarisana-akcija", 1)]))
    h = Healer()
    case = h.detect("r3-agent", [HRM.Finding(HRM.AGENT, "injekcija", "x", HRM.HIGH)])
    h.treat(case)
    assert case.actions == ["boundary-reset"]
    assert [a for _, a in case.pending] == ["nova-nedeklarisana-akcija"]
    assert any(it["payload"]["action"] == "nova-nedeklarisana-akcija"
               for it in store().open_items("heal"))


def test_restore_from_seal_keeps_the_tampered_copy(operator, tmp_path):
    from pse_r import config
    from pse_r.shared_lib import reports as RP
    config.DIR_REPORTS.mkdir(parents=True, exist_ok=True)
    p = config.DIR_REPORTS / "r3-izvjestaj.md"
    p.write_text("original", encoding="utf-8")
    RP.seal(p)
    import os
    os.chmod(p, 0o644)
    p.write_text("izmijenjeno", encoding="utf-8")
    assert RP.restore(p)
    assert p.read_text(encoding="utf-8") == "original"
    kept = list((config.DIR_STATE / "forensic").glob("r3-izvjestaj.md.*.tampered"))
    assert kept and kept[0].read_text(encoding="utf-8") == "izmijenjeno"
