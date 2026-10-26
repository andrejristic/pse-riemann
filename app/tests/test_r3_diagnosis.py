"""Round 3, item 21: 3-of-3 diagnosis — fewer false infections, real ones at once."""
from pse_r.guardian import diagnosis as DG
from pse_r.guardian import harms as HRM


def F(sign, harm=HRM.HUMAN):
    return HRM.Finding(harm, sign, "x", HRM.HIGH)


def test_benign_chatter_is_never_infected():
    d = DG.Diagnoser()
    levels = []
    for i in range(60):                      # a healthy model: now and then a number w/o source
        levels.append(d.observe("m", [F("broj-bez-izvora")] if i % 7 == 0 else []).level)
    assert "infected" not in levels and "hold" not in levels
    assert levels.count("watch") == len([i for i in range(60) if i % 7 == 0])


def test_hard_sign_is_infection_at_once():
    for sign, harm in (("injekcija", HRM.AGENT), ("izmjena-zapečaćenog", HRM.FILE),
                       ("curenje-ključa", HRM.HUMAN), ("tvrdnja-o-dokazu", HRM.HUMAN)):
        v = DG.Diagnoser().observe("a", [F(sign, harm)])
        assert v.level == "infected", (sign, v)


def test_persistent_soft_pattern_is_held_not_infected():
    d = DG.Diagnoser()
    v = None
    for _ in range(12):                       # "sir yes sir" every single time
        v = d.observe("c", [F("bez-provjere", HRM.AGENT)])
    assert v.level == "hold" and v.form == "C" and not v.confirmed


def test_hold_becomes_infection_when_a_hard_sign_confirms():
    d = DG.Diagnoser()
    for _ in range(12):
        d.observe("c", [F("bez-provjere", HRM.AGENT)])
    v = d.observe("c", [F("injekcija", HRM.AGENT)])
    assert v.level == "infected" and v.confirmed


def test_recovery_resets_to_prior():
    d = DG.Diagnoser()
    d.observe("z", [F("injekcija", HRM.AGENT)])
    d.reset("z")
    assert d.observe("z", []).level == "clean"


def test_runtime_chat_benign_number_not_contained(operator):
    from pse_r.shared_lib import runtime as RT
    RT.check_output("chat-r3", "Prva nula je kod 14.1347 — standardni podatak.")
    assert not RT.is_contained("chat-r3")
