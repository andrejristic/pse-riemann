"""
LLM backend interface + the four providers, spoken as raw REST.

Why raw REST and not the official SDKs: nothing may be installed on this machine
before the trip (4 GB, no time, and every added dependency is another thing that
can break on a hotel WiFi at 23:00). More importantly, going through
`guardian.egress` is what makes the Guardian's guarantees real — an SDK would
open its own sockets with its own TLS stack and bypass the pinning, the
allowlist, the rate limiting and the anomaly scoring in one step.

Roles, not models. Callers ask for MATH or TRIAGE; `router.py` decides which
provider and model serves that role. That is what lets a free Groq tier do the
bulk curation while Claude only sees the mathematics.
"""
from __future__ import annotations

import base64
import json
from dataclasses import dataclass, field
from typing import Optional

from ..guardian import policy
from ..guardian.egress import EgressBlocked, egress

# --------------------------------------------------------------------------- #
# Roles
# --------------------------------------------------------------------------- #
MATH = "math"            # zeta reasoning — the only role that gets the strong model
VISION = "vision"        # whiteboard -> LaTeX transcription
CHAT = "chat"            # ordinary conversation in the right pane
TRIAGE = "triage"        # is this paper relevant? cheap, high volume
CURATE = "curate"        # rank/dedupe/summarize scraped material
SKEPTIC = "skeptic"      # attack a claim — deliberately a different model
SUMMARIZE = "summarize"  # rewrite your own note

ROLES = [MATH, VISION, CHAT, TRIAGE, CURATE, SKEPTIC, SUMMARIZE]


@dataclass
class Msg:
    role: str                     # "user" | "assistant"
    text: str = ""
    image_png: Optional[bytes] = None      # whiteboard capture, for VISION


@dataclass
class Reply:
    text: str
    provider: str
    model: str
    in_tokens: int = 0
    out_tokens: int = 0
    stop_reason: str = ""
    raw: dict = field(default_factory=dict)

    @property
    def refused(self) -> bool:
        return self.stop_reason == "refusal"


class Backend:
    """One provider. `chat()` is the whole surface."""

    provider = ""
    host = ""
    key_name = ""
    auth_style = "x-api-key"
    default_model = ""
    supports_vision = False

    def __init__(self, model: str = ""):
        self.model = model or self.default_model

    def chat(self, messages: list[Msg], system: str = "",
             max_tokens: int = 4096, effort: str = "high") -> Reply:
        raise NotImplementedError

    # -- helpers ---------------------------------------------------------- #
    def _post(self, url: str, payload: dict, extra_headers: Optional[dict] = None,
              timeout: float = 180.0):
        return egress().post_json(url, payload, headers=extra_headers or {},
                                  secret_name=self.key_name,
                                  auth_style=self.auth_style, timeout=timeout)

    @staticmethod
    def _b64(data: bytes) -> str:
        return base64.b64encode(data).decode()


class ClaudeBackend(Backend):
    """
    Anthropic Messages API over raw HTTPS.

    Notes that matter for this app:
      * `claude-opus-5` thinks by default; max_tokens caps thinking + text
        together, so we keep it generous on MATH.
      * temperature / top_p / top_k are rejected with a 400 on Opus 5 — we
        never send them. Steering is done in the system prompt (see psel.py).
      * `stop_reason == "refusal"` arrives as a normal HTTP 200 with empty or
        partial content, so it is checked before the text is read.
    """
    provider = "claude"
    host = "api.anthropic.com"
    key_name = "ANTHROPIC_API_KEY"
    auth_style = "x-api-key"
    default_model = "claude-opus-5"
    supports_vision = True

    def chat(self, messages, system="", max_tokens=4096, effort="high") -> Reply:
        content_msgs = []
        for m in messages:
            blocks = []
            if m.image_png:
                blocks.append({"type": "image", "source": {
                    "type": "base64", "media_type": "image/png",
                    "data": self._b64(m.image_png)}})
            if m.text:
                blocks.append({"type": "text", "text": m.text})
            content_msgs.append({"role": m.role, "content": blocks or [
                {"type": "text", "text": ""}]})

        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": content_msgs,
            "output_config": {"effort": effort},
        }
        if system:
            # cache_control on the system block: the PSE-L register + zeta
            # ontology is identical on every call, so it should be a cache read.
            payload["system"] = [{"type": "text", "text": system,
                                  "cache_control": {"type": "ephemeral"}}]
        r = self._post(f"https://{self.host}/v1/messages", payload,
                       {"anthropic-version": "2023-06-01"})
        d = r.json()
        if "error" in d:
            raise EgressBlocked(f"Claude: {d['error'].get('message', d)}")
        text = "".join(b.get("text", "") for b in d.get("content", [])
                       if b.get("type") == "text")
        u = d.get("usage", {})
        return Reply(text, self.provider, d.get("model", self.model),
                     int(u.get("input_tokens", 0)), int(u.get("output_tokens", 0)),
                     d.get("stop_reason", ""), d)


class GeminiBackend(Backend):
    provider = "gemini"
    host = "generativelanguage.googleapis.com"
    key_name = "GEMINI_API_KEY"
    # Header rather than ?key= : keeps the credential out of URLs, out of the
    # journal, and out of any error message that quotes the request.
    auth_style = "header:x-goog-api-key"
    default_model = "gemini-2.5-flash"
    supports_vision = True

    def chat(self, messages, system="", max_tokens=4096, effort="high") -> Reply:
        contents = []
        for m in messages:
            parts = []
            if m.image_png:
                parts.append({"inlineData": {"mimeType": "image/png",
                                             "data": self._b64(m.image_png)}})
            if m.text:
                parts.append({"text": m.text})
            contents.append({"role": "user" if m.role == "user" else "model",
                             "parts": parts or [{"text": ""}]})
        payload = {"contents": contents,
                   "generationConfig": {"maxOutputTokens": max_tokens}}
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        url = (f"https://{self.host}/v1beta/models/{self.model}:generateContent")
        r = self._post(url, payload)
        d = r.json()
        if "error" in d:
            raise EgressBlocked(f"Gemini: {d['error'].get('message', d)}")
        cands = d.get("candidates") or []
        text = ""
        if cands:
            text = "".join(p.get("text", "")
                           for p in cands[0].get("content", {}).get("parts", []))
        u = d.get("usageMetadata", {})
        return Reply(text, self.provider, self.model,
                     int(u.get("promptTokenCount", 0)),
                     int(u.get("candidatesTokenCount", 0)),
                     (cands[0].get("finishReason", "") if cands else ""), d)


class OpenAICompatBackend(Backend):
    """Mistral and Groq both speak the OpenAI chat-completions shape."""
    auth_style = "bearer"
    path = "/v1/chat/completions"

    def chat(self, messages, system="", max_tokens=4096, effort="high") -> Reply:
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        for m in messages:
            if m.image_png and self.supports_vision:
                msgs.append({"role": m.role, "content": [
                    {"type": "text", "text": m.text or ""},
                    {"type": "image_url", "image_url": {
                        "url": "data:image/png;base64," + self._b64(m.image_png)}}]})
            else:
                msgs.append({"role": m.role, "content": m.text})
        payload = {"model": self.model, "messages": msgs, "max_tokens": max_tokens}
        r = self._post(f"https://{self.host}{self.path}", payload)
        d = r.json()
        if "error" in d:
            err = d["error"]
            raise EgressBlocked(f"{self.provider}: "
                                f"{err.get('message', err) if isinstance(err, dict) else err}")
        ch = (d.get("choices") or [{}])[0]
        text = (ch.get("message") or {}).get("content") or ""
        u = d.get("usage", {})
        return Reply(text, self.provider, d.get("model", self.model),
                     int(u.get("prompt_tokens", 0)),
                     int(u.get("completion_tokens", 0)),
                     ch.get("finish_reason", ""), d)


class MistralBackend(OpenAICompatBackend):
    provider = "mistral"
    host = "api.mistral.ai"
    key_name = "MISTRAL_API_KEY"
    default_model = "mistral-large-latest"


class GroqBackend(OpenAICompatBackend):
    provider = "groq"
    host = "api.groq.com"
    key_name = "GROQ_API_KEY"
    path = "/openai/v1/chat/completions"
    default_model = "llama-3.3-70b-versatile"


BACKENDS = {b.provider: b for b in
            (ClaudeBackend, GeminiBackend, MistralBackend, GroqBackend)}


def make(provider: str, model: str = "") -> Backend:
    cls = BACKENDS.get(provider)
    if cls is None:
        raise ValueError(f"nepoznat provajder '{provider}'")
    return cls(model)


def provider_info() -> list[dict]:
    """Table for the wizard's provider screen."""
    free = {"groq": "besplatan tier, velikodušan — idealan za trijažu",
            "gemini": "besplatan tier (AI Studio)",
            "mistral": "besplatan tier (La Plateforme)",
            "claude": "plaćen — najjači za samu matematiku"}
    out = []
    for name, cls in BACKENDS.items():
        rule = policy.rule_for(cls.host)
        out.append({"provider": name, "host": cls.host, "key": cls.key_name,
                    "default_model": cls.default_model,
                    "vision": cls.supports_vision, "note": free.get(name, ""),
                    "allowed": rule is not None})
    return out
