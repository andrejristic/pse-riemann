"""
The method pack and its mandatory reproduction test (plan F8).

A method pack is one self-contained file describing a method well enough that the
app can re-derive its headline number on its own:

    {
      "name": "liu",
      "family": "liu",                 # which exponent family (liu | xs | line)
      "source": "arxiv:2610.12234",    # resolvable reference
      "claimed_B": 0.874957019420,     # the number the paper states
      "dlo": 1e-6,                     # admissible lower edge of δ
      "tol": 1e-7,                     # how close our pipeline must land
      "exact_poly": "1188*xi**3 - ...", # optional, for the record
      "note": "...", "tags": ["qrh","liu"]
    }

The reproduction test is deterministic and stands ABOVE any model: our explorer
computes B* from the recipe and the pack is reproduced only if |B* − claimed_B|
≤ tol. A pack whose recipe does not reproduce the paper's number is refused at
the door, no matter who proposed it. This is the whole point of the "open door":
new results enter as data to be re-derived, not as assertions to be trusted.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from . import core as C
from .registry import MethodSpec

_FAMILIES = {"liu", "xs", "line"}


class PackError(Exception):
    pass


@dataclass
class MethodPack:
    name: str
    family: str
    source: str
    claimed_B: float
    dlo: float = 1 / 8
    tol: float = 1e-7
    exact_poly: str = ""
    note: str = ""
    tags: list = field(default_factory=list)

    # -- parsing -------------------------------------------------------------- #
    @classmethod
    def from_dict(cls, d: dict) -> "MethodPack":
        if not isinstance(d, dict):
            raise PackError("paket nije objekat")
        missing = [k for k in ("name", "family", "source", "claimed_B") if k not in d]
        if missing:
            raise PackError(f"paket nema obavezna polja: {missing}")
        if d["family"] not in _FAMILIES:
            raise PackError(f"nepoznata familija '{d['family']}' (dozvoljeno: "
                            f"{sorted(_FAMILIES)})")
        try:
            claimed = float(d["claimed_B"])
        except (TypeError, ValueError):
            raise PackError(f"claimed_B nije broj: {d['claimed_B']!r}")
        if not (0.0 < claimed < 1.0):
            raise PackError(f"claimed_B van (0,1): {claimed}")
        return cls(
            name=str(d["name"]).strip(),
            family=str(d["family"]),
            source=str(d["source"]).strip(),
            claimed_B=claimed,
            dlo=float(d.get("dlo", 1 / 8)),
            tol=float(d.get("tol", 1e-7)),
            exact_poly=str(d.get("exact_poly", "")),
            note=str(d.get("note", "")),
            tags=list(d.get("tags", [])),
        )

    @classmethod
    def from_file(cls, path: Path) -> "MethodPack":
        try:
            raw = Path(path).read_text(encoding="utf-8")
        except OSError as e:
            raise PackError(f"ne mogu da pročitam paket: {e}") from e
        try:
            return cls.from_dict(json.loads(raw))
        except json.JSONDecodeError as e:
            raise PackError(f"paket nije ispravan JSON: {e}") from e

    def to_dict(self) -> dict:
        return {"name": self.name, "family": self.family, "source": self.source,
                "claimed_B": self.claimed_B, "dlo": self.dlo, "tol": self.tol,
                "exact_poly": self.exact_poly, "note": self.note, "tags": self.tags}

    def spec(self) -> MethodSpec:
        return MethodSpec(self.name, self.family, self.source, self.claimed_B,
                          dlo=self.dlo, exact_poly=self.exact_poly, note=self.note,
                          tags=list(self.tags))


def reproduce(pack: MethodPack, tol: Optional[float] = None,
              check_poly: bool = False) -> dict:
    """
    Run the deterministic reproduction test. Returns a dict with:
      ok          |computed_B − claimed_B| ≤ tol
      computed_B  what our pipeline derives
      claimed_B   what the pack asserts
      error       the absolute difference
      poly_ok     None, or whether the exact minimal polynomial agrees too
      reading     a one-line human reading
    Never raises for a numeric mismatch — that is a verdict, not an error.
    """
    tol = pack.tol if tol is None else tol
    opt = pack.spec().optimum()
    err = abs(opt.B - pack.claimed_B)
    ok = err <= tol

    poly_ok = None
    if check_poly and pack.family in ("liu", "xs"):
        try:
            _poly, root = C.exact_polynomial(pack.family)
            poly_ok = abs(root - pack.claimed_B) <= max(tol, 1e-9)
        except Exception:                                  # noqa: BLE001
            poly_ok = None

    walls = C.broken_walls(opt.B, opt.l, opt.b, opt.k)
    if ok:
        reading = (f"reprodukovano: naš pipeline daje B*={opt.B:.12f}, rad tvrdi "
                   f"{pack.claimed_B:.12f} (razlika {err:.2e} ≤ tol {tol:.0e}).")
    else:
        reading = (f"NIJE reprodukovano: naš pipeline daje B*={opt.B:.12f}, rad "
                   f"tvrdi {pack.claimed_B:.12f} (razlika {err:.2e} > tol {tol:.0e}).")
    return {"ok": ok, "computed_B": opt.B, "claimed_B": pack.claimed_B,
            "error": err, "poly_ok": poly_ok, "broken_walls": walls,
            "optimum": {"B": opt.B, "l": opt.l, "b": opt.b, "k": opt.k},
            "reading": reading}
