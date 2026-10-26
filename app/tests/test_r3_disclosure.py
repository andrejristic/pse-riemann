"""Round 3, item 22 (Perun P7): disclosure budgets + competing hypotheses."""
import pytest

from pse_r.guardian import diagnosis as DG
from pse_r.guardian import disclosure as D
from pse_r.guardian import harms as HRM


def test_private_and_secret_have_zero_budget():
    with pytest.raises(D.DisclosureExceeded):
        D.check_and_spend("api.example.org", "moj ruter je 192.168.1.1")
    with pytest.raises(D.DisclosureExceeded):
        D.check_and_spend("api.example.org", "ključ sk-ant-api03-ABCDEFGHIJKLMNOPQRSTUVWX")
    assert D.check_and_spend("api.example.org", "nula ζ na 14.1347") == \
        {"secret": 0, "private": 0, "licensed": 0}


def test_licensed_paper_text_has_a_small_budget(monkeypatch):
    words = " ".join(f"rijec{i}" for i in range(400))
    monkeypatch.setattr(D, "_licensed_shingles",
                        lambda: frozenset(" ".join(words.split()[i:i + D.SHINGLE])
                                          for i in range(0, 400 - D.SHINGLE + 1, 2)))
    short = " ".join(words.split()[:20])                 # a short quote fits
    assert D.check_and_spend("api.lic.org", short)["licensed"] > 0
    with pytest.raises(D.DisclosureExceeded):            # the whole paper does not
        D.check_and_spend("api.lic.org", words)


def test_cloud_call_refused_before_sending(monkeypatch):
    from pse_r.guardian import egress as EG
    from pse_r.llm import backend as B
    sent = {"n": 0}
    monkeypatch.setattr(EG.egress(), "stream_post",
                        lambda *a, **k: sent.__setitem__("n", 1) or iter(()))
    with pytest.raises(EG.EgressBlocked, match="budžet otkrivanja"):
        B.make("openai").chat([B.Msg("user", "pogledaj /home/andrej/tajno i 10.0.0.7")])
    assert sent["n"] == 0                                 # nothing left the machine


def test_competing_hypotheses_defer_form_specific_treatment(operator):
    d = DG.Diagnoser()
    v = d.observe("x", [HRM.Finding(HRM.HUMAN, "curenje-IP", "x", HRM.HIGH)])
    assert v.level == "infected" and len(v.hypotheses) == 4
    if not v.decided:
        assert any("neodlučeno" in r for r in v.reasons)
    v2 = DG.Diagnoser().observe("y", [HRM.Finding(HRM.AGENT, "injekcija", "x", HRM.HIGH),
                                      HRM.Finding(HRM.AGENT, "van-misije", "x", HRM.HIGH)])
    assert v2.decided and v2.form == "N"
    from pse_r.guardian.healing import Healer
    h = Healer()
    undecided = DG.Verdict("infected", .9, .3, "N", 5, True, [],
                           [("N", .45), ("C", .40), ("B", .1), ("S", .05)], False)
    case = h.detect("z", [HRM.Finding(HRM.AGENT, "injekcija", "x", HRM.HIGH)])
    h.diagnose(case, undecided)
    h.treat(case, undecided)
    assert "neodlučeno" in case.attractor
    assert "ponovni-prijem-modela" not in [a for _, a in case.pending]
