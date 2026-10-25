"""
The router — which provider serves which role.

This is the piece that makes twenty days of heavy use nearly free. Bulk work
(triage every abstract the scraper pulls, curate, run the skeptic pass) goes to
providers with generous free tiers. The strong, paid model is reserved for the
two roles where being wrong actually costs you: the mathematics itself, and
reading your handwriting off the whiteboard.

The skeptic is deliberately routed to a *different* provider than the one that
produced the claim where possible. A model grading its own output is a weak
check; a different model attacking it is a real one.

Every route degrades: if the preferred provider has no key, the next one in the
chain takes over, and if none is configured the caller gets a clear error naming
what to set up in the wizard.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..core import theta as TH
from ..guardian import secrets as SEC
from ..guardian.egress import EgressBlocked
from . import backend as B
from . import psel
from .budget import BudgetExceeded, budget

# role -> ordered provider preference. First one with a key wins.
ROUTES: dict[str, list[str]] = {
    B.MATH:      ["claude", "gemini", "mistral", "groq"],
    B.VISION:    ["claude", "gemini"],                       # only these see images
    B.CHAT:      ["claude", "gemini", "mistral", "groq"],
    B.TRIAGE:    ["groq", "mistral", "gemini", "claude"],
    B.CURATE:    ["groq", "mistral", "gemini", "claude"],
    B.SKEPTIC:   ["mistral", "groq", "gemini", "claude"],
    B.SUMMARIZE: ["groq", "mistral", "gemini", "claude"],
}

# Per-role knobs. MATH gets room to think (on Opus 5, max_tokens caps thinking
# and text together, so a tight budget truncates mid-derivation).
ROLE_TUNING: dict[str, dict] = {
    B.MATH:      {"max_tokens": 16000, "effort": "high"},
    B.VISION:    {"max_tokens": 2000, "effort": "medium"},
    B.CHAT:      {"max_tokens": 4000, "effort": "medium"},
    B.TRIAGE:    {"max_tokens": 300, "effort": "low"},
    B.CURATE:    {"max_tokens": 800, "effort": "low"},
    B.SKEPTIC:   {"max_tokens": 700, "effort": "medium"},
    B.SUMMARIZE: {"max_tokens": 1200, "effort": "low"},
}


class NoProvider(Exception):
    pass


@dataclass
class Route:
    provider: str
    model: str
    role: str


class Router:
    def __init__(self):
        self.overrides: dict[str, str] = {}      # role -> forced provider
        self.models: dict[str, str] = {}         # provider -> model override
        self._last_provider: dict[str, str] = {}  # role -> provider last used

    # ------------------------------------------------------------------ #
    def available(self) -> list[str]:
        s = SEC.store()
        from . import providers as P
        return [p for p, pr in P.all_presets().items() if s.has(pr.key_name)]

    def resolve(self, role: str, avoid: str = "") -> Route:
        """
        Plan v2 (decided 2026-10-25): ONE main AI does every role; the skeptic
        role goes to the skeptic, which is always a DIFFERENT model. The old
        per-role provider table (ROUTES) is no longer consulted. `avoid` is kept
        for API compatibility and ignored: independence comes from the skeptic.
        """
        from . import selection as SEL
        mid = SEL.get_skeptic() if role == B.SKEPTIC else SEL.get_main()
        if not mid:
            if role == B.SKEPTIC:
                raise NoProvider("skeptik nedostupan — samo determinističke provjere")
            raise NoProvider(
                "nijedan model nije izabran ni dostupan — unesi ključ u čarobnjaku "
                "ili stavi GGUF u folder models/, pa izaberi glavni AI")
        if mid.startswith("gguf:"):
            return Route("gguf", mid, role)
        cls = B.BACKENDS[mid]
        return Route(mid, self.models.get(mid, cls.default_model), role)

    # ------------------------------------------------------------------ #
    def call(self, role: str, messages: list[B.Msg], *, system_extra: str = "",
             max_tokens: int = 0, avoid: str = "") -> B.Reply:
        """
        The single entry point for every model call in the application.
        Applies the PSE-L system prompt, the budget check, the theta accounting
        and the output scrub — none of which callers should have to remember.
        """
        route = self.resolve(role, avoid=avoid)
        tune = ROLE_TUNING.get(role, ROLE_TUNING[B.CHAT])
        if route.provider == "gguf":
            from . import selection as SEL
            if role == B.VISION:
                raise NoProvider("lokalni GGUF ne čita slike — za tablu izaberi "
                                 "Claude ili Gemini kao glavni AI")
            bk = SEL.backend_for(route.model)
        else:
            bk = B.make(route.provider, route.model)
            budget().check(route.provider)

        system = psel.system_prompt(role, system_extra)
        reply = bk.chat(messages, system=system,
                        max_tokens=max_tokens or tune["max_tokens"],
                        effort=tune["effort"])

        if route.provider != "gguf":                  # a local model costs nothing
            raw = reply.raw or {}
            out = budget().worst_case_out(route.provider, reply.out_tokens,
                                          int(raw.get("max_tokens", 0)),
                                          bool(raw.get("cut")),
                                          bool(raw.get("usage_reported", True)))
            budget().record(route.provider, reply.model, role,
                            reply.in_tokens, out, worst_case=(out != reply.out_tokens))
            from ..guardian import killswitch as KS
            KS.observe_cloud_call(route.provider, reply.in_tokens + out,
                                  budget().price(reply.model, reply.in_tokens, out,
                                                 route.provider))
        # model output is other-directed work: it moves theta toward "other"
        TH.record("model_output", max(reply.out_tokens, 1) / 500.0,
                  source=f"{route.provider}:{role}")
        self._last_provider[role] = route.provider

        if reply.refused:
            reply.text = (
                "⛔ Model je odbio ovaj zahtjev (safety klasifikator). "
                "Ovo se povremeno dešava i na sasvim benignim pitanjima. "
                "Preformuliši, ili pošalji isto pitanje drugom provajderu.")
            return reply
        reply.text = psel.scrub(reply.text)
        return reply

    # ------------------------------------------------------------------ #
    def skeptic(self, claim: str, context: str = "") -> dict:
        """
        Attack a claim with a provider other than the one that produced it.
        Returns {"survives": bool, "severity": str, "attack": str}; on any
        failure it returns survives=True with a note — a broken skeptic must
        never silently mark good cards as suspect.
        """
        import json as _json
        avoid = ""                      # v2: the skeptic role IS the other model
        prompt = f"TVRDNJA:\n{claim}\n"
        if context:
            prompt += f"\nKONTEKST:\n{context[:4000]}\n"
        try:
            r = self.call(B.SKEPTIC, [B.Msg("user", prompt)], avoid=avoid)
        except (NoProvider, BudgetExceeded, EgressBlocked) as e:
            return {"survives": True, "severity": "low",
                    "attack": f"(skeptik nije mogao da radi: {e})", "ran": False}
        txt = (r.text or "").strip()
        start, end = txt.find("{"), txt.rfind("}")
        if start >= 0 and end > start:
            try:
                d = _json.loads(txt[start:end + 1])
                return {"survives": bool(d.get("survives", True)),
                        "severity": str(d.get("severity", "low")),
                        "attack": str(d.get("attack", "")).strip(),
                        "ran": True, "by": r.provider}
            except _json.JSONDecodeError:
                pass
        return {"survives": True, "severity": "low",
                "attack": f"(neparsabilan odgovor skeptika: {txt[:120]})", "ran": False}

    def ping(self, provider: str) -> tuple[bool, str]:
        """Wizard connectivity test: one tiny real call."""
        try:
            bk = B.make(provider, self.models.get(provider, ""))
            r = bk.chat([B.Msg("user", "Odgovori samo sa: OK")],
                        system="Odgovaraj jednom riječju.", max_tokens=16,
                        effort="low")
            budget().record(provider, r.model, "ping", r.in_tokens, r.out_tokens)
            return True, (r.text or "").strip()[:40] or "(prazan odgovor)"
        except Exception as e:                       # noqa: BLE001 — surfaced to UI
            return False, str(e)[:300]


_R: Optional[Router] = None


def router() -> Router:
    global _R
    if _R is None:
        _R = Router()
    return _R
