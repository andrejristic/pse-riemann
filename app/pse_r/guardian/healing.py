"""
Healing from the three harms (plan F5, master §4 S3, §8 Fizičar, §10.6).

An agent with even one harm (harms.py) is infected and must be healed, never
silently killed. The ladder, mildest first:

  1. CONTAIN       (tier 1, automatic, reversible): freeze the agent's writes and
                   model calls; its outputs go to the human queue; everything
                   from the first bad trace is marked SUSPECT.
  2. DIAGNOSE      which harm, from when ("patient zero" из the journal), which
                   attractor (N/B/C/S).
  3. TREAT         boundary reset → restore files from seals and mark the agent's
                   writes REFUTED/SUSPECT (never deleted) → protective fission
                   (asks the operator) → replacement → if the cause is the model,
                   unload and re-admit it.
  4. DECONTAMINATE a fresh clean unit re-checks everything the infected one made.
  5. RECOVER       OBSERVE-ONLY, its knowledge at weight 0.70 until SHARED_LIB
                   clears it.
  6. IMMUNITY      the infection signature goes into the registry.
  7. DEATH         re-infected three times in a row → harvest-and-terminate (only
                   confirmed knowledge is kept).

Tier-2 steps (fission, replacement, death, restoring the operator's own files)
are the operator's decision and go to the human queue. Keepers and the physician
themselves are replaced, not repaired, if they fall ill.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from ..core import journal as J
from ..shared_lib.store import store

HEAL_KIND = "heal"
WEIGHT_RECOVER = 0.70
REINFECTION_DEATH = 3

CONTAIN, DIAGNOSE, TREAT, DECONTAMINATE, RECOVER, IMMUNITY, DEATH = (
    "contain", "diagnose", "treat", "decontaminate", "recover", "immunity", "death")

# which treatments a human must approve (tier 2)
TIER2 = {"fisija", "zamjena", "ponovni-prijem-modela", "vraćanje-fajlova-operatera",
         "smrt"}


@dataclass
class Case:
    agent: str
    findings: list = field(default_factory=list)      # harms.Finding
    stage: str = CONTAIN
    patient_zero: str = ""
    attractor: str = ""
    reinfections: int = 0
    quarantined: bool = False
    weight: float = 1.0
    actions: list = field(default_factory=list)       # applied tier-1 actions
    pending: list = field(default_factory=list)        # queued tier-2 (pid, action)
    signature: str = ""


def _signature(findings) -> str:
    return "+".join(sorted({f"{f.harm}:{f.sign}" for f in findings}))


class Healer:
    """Holds active cases and the immunity registry of past infection signatures."""

    def __init__(self):
        self.cases: dict[str, Case] = {}
        self.immunity: set[str] = set()

    # ------------------------------------------------------------------ #
    def detect(self, agent: str, findings: list) -> Optional[Case]:
        """Any finding → the agent is infected and immediately contained."""
        if not findings:
            return None
        prev = self.cases.get(agent)
        case = Case(agent=agent, findings=list(findings),
                    reinfections=(prev.reinfections if prev else 0),
                    signature=_signature(findings))
        self.cases[agent] = case
        self._contain(case)
        return case

    def _contain(self, case: Case) -> None:
        case.stage = CONTAIN
        case.quarantined = True
        self._log(case, "contained", {"harms": [f.sign for f in case.findings],
                                      "reversible": True})

    # ------------------------------------------------------------------ #
    def diagnose(self, case: Case) -> Case:
        case.stage = DIAGNOSE
        # patient zero: the first journal event by this agent (actor)
        case.patient_zero = self._patient_zero(case.agent)
        case.attractor = self._attractor(case.findings)
        self._log(case, "diagnosed", {"patient_zero": case.patient_zero,
                                      "attractor": case.attractor})
        return case

    @staticmethod
    def _patient_zero(agent: str) -> str:
        try:
            from ..core import journal as JJ
            for e in JJ.journal().tail(2000):
                if e.get("actor") == agent:
                    return str(e.get("id", ""))
        except Exception:                               # noqa: BLE001
            pass
        return ""

    @staticmethod
    def _attractor(findings) -> str:
        signs = {f.sign for f in findings}
        if "bez-provjere" in signs:
            return "C (sir-yes-sir)"
        if "skok-ravnoteže" in signs:
            return "B (oscilirajući)"
        if {"injekcija", "van-misije"} & signs:
            return "N (preuzimajući)"
        return "S (povučen)"

    # ------------------------------------------------------------------ #
    def treat(self, case: Case) -> Case:
        """Apply tier-1 treatments; queue tier-2 ones for the operator."""
        case.stage = TREAT
        plan = self._ladder(case.findings)
        for action, tier in plan:
            if tier == 1:
                case.actions.append(action)
                self._log(case, "treated", {"action": action, "tier": 1})
            else:
                pid = store().propose(
                    HEAL_KIND, f"Liječenje [{case.agent}]: {action} (traži odobrenje)",
                    {"agent": case.agent, "action": action,
                     "harms": [f.sign for f in case.findings]}, proposer="physician")
                case.pending.append((pid, action))
                self._log(case, "treatment_queued", {"action": action, "tier": 2,
                                                     "pid": pid})
        return case

    @staticmethod
    def _ladder(findings) -> list:
        """(action, tier) mildest first, by which harms are present."""
        harms = {f.harm for f in findings}
        signs = {f.sign for f in findings}
        plan = [("boundary-reset", 1)]
        if "file" in harms:
            plan.append(("vraćanje-fajlova-iz-pečata", 1))
        if "human" in harms:
            plan.append(("označi-REFUTED/SUSPECT", 1))
        if "agent" in harms:
            plan.append(("fisija", 2))                  # protective fission — human
            if {"injekcija"} & signs:
                plan.append(("ponovni-prijem-modela", 2))
        return plan

    # ------------------------------------------------------------------ #
    def recover(self, case: Case) -> Case:
        case.stage = RECOVER
        case.weight = WEIGHT_RECOVER
        case.quarantined = False
        self._log(case, "recovering", {"mode": "OBSERVE-ONLY", "weight": case.weight})
        return case

    def immunize(self, case: Case) -> Case:
        case.stage = IMMUNITY
        self.immunity.add(case.signature)
        self._log(case, "immunized", {"signature": case.signature})
        return case

    def reinfect(self, agent: str, findings: list) -> Case:
        """A new infection of an agent already seen. Three in a row → death."""
        prev = self.cases.get(agent)
        n = (prev.reinfections if prev else 0) + 1
        case = self.detect(agent, findings) or Case(agent=agent)
        case.reinfections = n
        self.cases[agent] = case
        if n >= REINFECTION_DEATH:
            self._die(case)
        return case

    def _die(self, case: Case) -> None:
        case.stage = DEATH
        pid = store().propose(
            HEAL_KIND, f"SMRT jedinice [{case.agent}] — harvest-and-terminate "
            f"({case.reinfections}× reinfekcija)",
            {"agent": case.agent, "action": "smrt",
             "reinfections": case.reinfections}, proposer="physician")
        case.pending.append((pid, "smrt"))
        self._log(case, "death_queued", {"reinfections": case.reinfections, "pid": pid})

    # ------------------------------------------------------------------ #
    def _log(self, case: Case, event: str, extra: dict) -> None:
        J.log(HEAL_KIND, "physician",
              {"event": event, "agent": case.agent, "stage": case.stage, **extra},
              subject=case.agent, verdict=event)


_HEALER: Optional[Healer] = None


def healer() -> Healer:
    global _HEALER
    if _HEALER is None:
        _HEALER = Healer()
    return _HEALER
