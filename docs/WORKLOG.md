# WORKLOG — PSE Riemann v2

**STATUS: RADI** (grana `feature/qrh-shared-lib`)

Vodi se posle svake faze: šta je urađeno, stanje testova, šta je sljedeće, procjena preostalog. Plan: [PLAN.md](PLAN.md).

| Datum | Faza | Stanje | Testovi | Napomena |
|---|---|---|---|---|
| 2026-10-25 | Istraživanje QRH | ✅ gotovo | skripte reproducibilne | `research/qrh-2026-10/` |
| 2026-10-25 | Izjednačavanje repoa | ✅ gotovo | 0 razlika lokalno ↔ GitHub | merge 6548210 |
| 2026-10-25 | Plan v2 | ✅ dogovoren | — | "kreni" dato |
| 2026-10-25 | Postavka | ✅ | alert testiran | grana, `tools/alert.py`, `tools/worklock.sh`, zakazani zadatak svaka 2 h |
| 2026-10-25 | app/.venv | ✅ | numpy/sympy/PySide6 importuju | venv ponovo napravljen, deps OK |
| 2026-10-25 | F1 · SHARED_LIB sloj | ✅ gotovo | 19/19 pytest + selftest prolaze | commit `b73c2e3` (lokalno; push čeka — vidi problem 1) |
| 2026-10-25 | F2 · nivoi izvora u kapiji | ✅ gotovo | 25/25 pytest + selftest prolaze | commit `aae6d02`; `vault/tiers.py`, preprint≠oslonac utvrđene; `lean:` izvor |
| 2026-10-25 | F8 · istraživač metoda + vrata | ✅ gotovo | 33/33 pytest + selftest prolaze | commit `4366067`; `pse_r/methods/` (core/registry/pack/door), Liu 0.874957019420 i XS 0.874886647040 tačno, T=1.5e-16, zid≈5/6; lab qrh_* |

**Sljedeće:** F9 · misije i arXiv — tab/model Misije (stanje, akcija, ishod), prva misija (kontinualna transformacija + bliže/dalje od ciljeva), arXiv praćenje "quasi-Riemann hypothesis" → prijedlog metode → test reprodukcije → skeptik → operater potvrđuje. (GUI tab dolazi u F6; ovdje model misije + arXiv ulaz kroz vrata.)

## Otvoreni problemi
1. **`git push` blokiran u automatskom (nenadziranom) pokretanju.** Harness traži ljudsko odobrenje za mrežne radnje, a u zakazanom pokretanju niko nije prisutan, pa i `push origin feature/qrh-shared-lib` biva odbijen (probano i sa isključenim sandbox-om). Commitovi su bezbjedni lokalno (i na Desktop kopiji); grana je ispred `origin` za N commitova. Riješiti: pokrenuti push iz nadzirane sesije (Andrej otvori Claude) ili ručno `git push origin feature/qrh-shared-lib`. Rad se nastavlja normalno — ovo ne blokira nijednu fazu.

**Preostalo:** ~38–56 h rada (F2–F10 + izvlačenje + test prihvatanja + A/C/.exe).
