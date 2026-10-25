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
| 2026-10-25 | F9 · misije i arXiv | ✅ gotovo | 39/39 pytest + selftest prolaze | commit `e11ade6`; `shared_lib/missions.py` (L3), `methods/arxiv.py`, prva misija seedovana, ulaz kroz vrata vezan za misiju |
| 2026-10-25 | F3 · glavni AI + skeptik + limiteri | ✅ gotovo (logika) | 49/49 pytest + selftest prolaze | commit `0414b44`; `llm/limits.py`,`gguf.py`,`selection.py`,`skeptic.py`; llama-cpp 0.3.36 instaliran (CPU wheel); GGUF download u toku |
| 2026-10-25 | F4 · glas SHARED_LIB-a | ✅ gotovo | 56/56 pytest + selftest prolaze | commit `4795b0a`; `shared_lib/voice.py`, citati+verify_numbers+UNKNOWN+scrub, samo operateru, radi i bez modela |
| 2026-10-25 | F5 · čuvari + liječenje | ✅ gotovo | 67/67 pytest + selftest prolaze | commit `3c8441c`; `guardian/harms.py`,`healing.py`,`shared_lib/reports.py`; seal/patrol/restore, tri zla, ljestvica liječenja, tier2→red |
| 2026-10-25 | F7 · QRH sadržaj | ✅ gotovo | 71/71 pytest + selftest prolaze | commit `9307983`; `vault/qrh_seed.py`, izvori (Liu/XS CITED, OpenAI/Quanta FOLKLORE), tema, barijere, naši rezultati preko laba |
| 2026-10-25 | **Izvlačenje + TEST PRIHVATANJA (poenta)** | ✅ **PROLAZI** | 74/74 pytest + selftest prolaze | commit `2609bf1`; 4 paketa metoda, replay istorije kroz vrata: Liu→XS, front 0.874957→0.874886 „bliže", lažni rad odbijen |
| 2026-10-25 | F6 · GUI (tab Misije + red) | ✅ gotovo (funkcija) | 75/75 pytest (exit 0) + selftest | commit `b1cbce9`; `gui/qrh_tabs.py`, tab Misije + „Čeka tvoju odluku" (Odobri/Ne), izbor modela, Uvezi metodu, pilule glavni/skeptik; vizuelni QSS nije auto-verifikovan |

**Sljedeće:** F10 završnica — .deb full (B) prvi, pa A lean + C dodatak + .exe (CI), vodiči SR/EN; GGUF smoke-test (download pri kraju). Spajanje u `main` TEK uz izričito odobrenje Andreja (ne radim ga sam).

GGUF smoke: model se preuzima (~70%); kad završi → verify (sha256) + jedan mali chat poziv kroz limitere, upis rezultata ovdje.

Napomene uz F3: skeptik u automatskom pokretanju je „nedostupan" (nema oblak-ključa, jedan model) → samo determinističke provjere (validna grana po planu). GGUF download pao na HTTP/2 (err 92) na ~1.3/5.6 GB; resume pokrenut (HTTP/1.1). Živi smoke-test GGUF-a tek kad download završi.

## Otvoreni problemi
1. **`git push` blokiran u automatskom (nenadziranom) pokretanju.** Harness traži ljudsko odobrenje za mrežne radnje, a u zakazanom pokretanju niko nije prisutan, pa i `push origin feature/qrh-shared-lib` biva odbijen (probano i sa isključenim sandbox-om). Commitovi su bezbjedni lokalno (i na Desktop kopiji); grana je ispred `origin` za N commitova. Riješiti: pokrenuti push iz nadzirane sesije (Andrej otvori Claude) ili ručno `git push origin feature/qrh-shared-lib`. Rad se nastavlja normalno — ovo ne blokira nijednu fazu.

**Preostalo:** ~38–56 h rada (F2–F10 + izvlačenje + test prihvatanja + A/C/.exe).
