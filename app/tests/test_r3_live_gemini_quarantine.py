"""Live test 0.2.0~rc1, finding 1: Gemini went into quarantine at every start.
The reachability check did GET https://<api-host>/ ; Google answers that with an
HTML 404 page; the egress read "API host returned HTML" as a captive portal and
quarantined the host. Fixed: the check never speaks HTTP (TLS + pin only), an HTML
ERROR page is not an attack, and a quarantine always asks the operator."""
import pytest

from pse_r.guardian import egress as EG
from pse_r.guardian import unit as GU
from pse_r.guardian import secrets as SEC
from pse_r.shared_lib.store import store

HOST = "generativelanguage.googleapis.com"


def _html(status):
    return EG.Response(status=status, headers={"content-type": "text/html; charset=UTF-8"},
                       body=b"<html><body>404. That's an error.</body></html>",
                       url=f"https://{HOST}/", elapsed=0.01, pin_state="match")


@pytest.fixture
def clean():
    g = GU.guardian()
    g.release(HOST, "test")
    for it in store().open_items(GU.QUARANTINE_KIND):
        store().withdraw(it["id"], "test", "reset")
    yield g
    g.release(HOST, "test")


def test_reachability_check_never_sends_http(clean, monkeypatch):
    from pse_r.llm import selection as SEL
    calls = []
    monkeypatch.setattr(SEL, "get_main", lambda: "gemini")
    monkeypatch.setattr(EG.Egress, "probe", lambda self, host, timeout=5.0: calls.append(host) or "match")
    monkeypatch.setattr(EG.Egress, "request", lambda *a, **k: pytest.fail("HTTP request in probe"))
    assert SEL.main_reachable() is True and calls == [HOST]


def test_google_html_404_is_an_error_not_an_attack(clean, monkeypatch):
    monkeypatch.setattr(EG.Egress, "_fetch", lambda self, *a, **k: _html(404))
    with pytest.raises(EG.EgressBlocked, match="nije napad"):
        EG.egress().request("GET", f"https://{HOST}/")
    assert not clean.is_quarantined(HOST)


def test_keyed_call_answered_with_html_200_is_quarantined_and_asks_operator(clean, monkeypatch, operator):
    GU.install_hooks()
    monkeypatch.setattr(EG.Egress, "_fetch", lambda self, *a, **k: _html(200))
    monkeypatch.setattr(SEC.store(), "get", lambda name: "test-key-123" if name == "GEMINI_API_KEY" else None)
    with pytest.raises(EG.EgressBlocked, match="captive"):
        EG.egress().request("POST", f"https://{HOST}/v1beta/models/x:generateContent",
                            secret_name="GEMINI_API_KEY", auth_style="header:x-goog-api-key", body=b"{}")
    assert clean.is_quarantined(HOST)
    items = [i for i in store().open_items(GU.QUARANTINE_KIND) if i["payload"]["host"] == HOST]
    assert len(items) == 1 and "Odobri = oslobodi" in items[0]["title"]
    with pytest.raises(EG.EgressBlocked, match="Čeka tvoju odluku"):
        EG.egress().request("GET", f"https://{HOST}/")         # the message says where to go
    store().decide(items[0]["id"], True)
    assert not clean.is_quarantined(HOST)
