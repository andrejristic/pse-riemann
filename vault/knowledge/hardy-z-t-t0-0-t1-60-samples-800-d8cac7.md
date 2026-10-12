---
id: hardy-z-t-t0-0-t1-60-samples-800-d8cac7
title: Hardy Z(t) — t0=0, t1=60, samples=800
type: numeric-fact
status: COMPUTED
author: lab
created: 2026-07-27T20:51:32-04:00
updated: 2026-07-27T20:51:32-04:00
lab_run: z_curve-20260727-205129-390875
script_sha256: 83bbf9c08dbc2fd239b563c3c2b42f636e3fcb018f921006c0c3b81b316c14ca
theta_at_write: 0
confidence: 1
tags:
  - lab
  - z_curve
---

**Pitanje.** Gdje su nule i kako izgledaju?

**Parametri.** `t0=0, t1=60, samples=800`

**Rezultat.**

| veličina | vrijednost |
|---|---|
| `t0` | 0.0 |
| `t1` | 60.0 |
| `step` | 0.075 |
| `zeros_found` | 13 |
| `smooth_prediction` | 11.9582 |
| `max_abs_Z` | 3.6635 |

Na intervalu [0, 60] Z mijenja znak **13 puta** — toliko nula leži NA kritičnoj pravoj u tom rasponu. Glatki član predviđa 11.958. Razlika je S(T), fluktuacija, i ona je mala i spora — to je cijela poenta.

Z je realna funkcija, pa se nule vide golim okom kao presjeci nule. Sve što ovdje vidiš je pod pretpostavkom da nijedna nula nije promašena — ako je korak preveliki, par nula može proći nezapaženo.

![Hardy Z(t)](../lab/z_curve-20260727-205129-390875/plot1.png)

---
Reproducibilnost: `lab/z_curve-20260727-205129-390875/script.py`, sha256 `83bbf9c08dbc2fd2…`, mpmath 1.3.0, trajanje 3.055 s.

Grana: [[tema-numerics]]
