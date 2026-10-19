---
id: eksplicitna-formula-x-x-max-100-n-zeros-40-72d7bb
title: Eksplicitna formula ψ(x) — x_max=100, n_zeros=40
type: numeric-fact
status: COMPUTED
author: lab
created: 2026-07-27T20:51:35-04:00
updated: 2026-07-27T20:51:35-04:00
lab_run: explicit-20260727-205132-0a77d0
script_sha256: 5ec8785f537a3c69c0ee064398457da17ec017757da0c3518498d1c0d0f4e769
theta_at_write: 0
confidence: 1
tags:
  - lab
  - explicit
---

**Pitanje.** Kako iz nula izlaze primovi?

**Parametri.** `x_max=100, n_zeros=40`

**Rezultat.**

| veličina | vrijednost |
|---|---|
| `x_max` | 100.0 |
| `n_zeros` | 40 |
| `max_abs_error` | 2.3658 |
| `mean_abs_error` | 0.4563 |
| `psi_exact_at_xmax` | 94.0453 |
| `psi_approx_at_xmax` | 94.5162 |

Glatka kriva x, korigovana sa **40 nula**, prati tačnu stepenastu funkciju ψ(x) sa srednjom greškom 0.456.

Svaka nula ρ = ½ + iγ doprinosi jedan talas amplitude 2√x/|ρ| i frekvencije γ. Nule su **frekvencije u spektru primova**. Dodaj ih dovoljno i glatka kriva se izlomi tačno na stepenicama primova i njihovih stepena.

Ovdje se vidi zašto je RH važna: amplituda svakog talasa je x^Re(ρ)/|ρ|. Ako sve nule imaju Re(ρ) = ½, greška u brojanju primova je reda √x. Nula sa Re(ρ) = 0.6 dala bi talas koji raste kao x^0.6 i trajno pokvario raspodjelu primova.

![Eksplicitna formula ψ(x)](../lab/explicit-20260727-205132-0a77d0/plot1.png)

---
Reproducibilnost: `lab/explicit-20260727-205132-0a77d0/script.py`, sha256 `5ec8785f537a3c69…`, mpmath 1.3.0, trajanje 2.53 s.

Grana: [[tema-pnt_error]]
