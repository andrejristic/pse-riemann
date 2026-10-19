---
id: self-test-numerike-n-points-8-9ece54
title: Self-test numerike — n_points=8
type: numeric-fact
status: COMPUTED
author: lab
created: 2026-07-27T20:51:29-04:00
updated: 2026-07-27T20:51:29-04:00
lab_run: selftest-20260727-205128-ec71a9
script_sha256: 0a4664fbda1d3c9bb5441e5af89597ca99b799dc0c79775259ab22d60978be4b
theta_at_write: 0
confidence: 1
tags:
  - lab
  - selftest
---

**Pitanje.** Da li se ovoj mašini može vjerovati?

**Parametri.** `n_points=8`

**Rezultat.**

| veličina | vrijednost |
|---|---|
| `points` | 8 |
| `max_functional_eq_residual` | 2.1526349109709204e-30 |
| `max_zero_error_vs_known` | 3.552713678800501e-15 |

Funkcionalna jednačina ζ(s) = χ(s)ζ(1−s) provjerena u 8 tačaka; najveći ostatak 2.153e-30.
Prvih 5 nula upoređeno sa objavljenim vrijednostima; najveća razlika 3.553e-15.

✅ Numerika je zdrava — ostalim eksperimentima se može vjerovati.

---
Reproducibilnost: `lab/selftest-20260727-205128-ec71a9/script.py`, sha256 `0a4664fbda1d3c9b…`, mpmath 1.3.0, trajanje 0.341 s.

Grana: [[tema-numerics]]
