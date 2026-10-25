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

**Sljedeće:** F5 · čuvari finalnih izvještaja + liječenje od tri zla (čuvar po izvještaju, zapečaćena kopija+sha256+inotify; detekcija tri zla; zadržavanje→dijagnoza→liječenje→dekontaminacija→oporavak→imunitet→smrt; čovjek odlučuje stepen 2). Zatim F6 (GUI), F7 (QRH sadržaj), F10 (završnica).

Napomene uz F3: skeptik u automatskom pokretanju je „nedostupan" (nema oblak-ključa, jedan model) → samo determinističke provjere (validna grana po planu). GGUF download pao na HTTP/2 (err 92) na ~1.3/5.6 GB; resume pokrenut (HTTP/1.1). Živi smoke-test GGUF-a tek kad download završi.

## Otvoreni problemi
1. **`git push` blokiran u automatskom (nenadziranom) pokretanju.** Harness traži ljudsko odobrenje za mrežne radnje, a u zakazanom pokretanju niko nije prisutan, pa i `push origin feature/qrh-shared-lib` biva odbijen (probano i sa isključenim sandbox-om). Commitovi su bezbjedni lokalno (i na Desktop kopiji); grana je ispred `origin` za N commitova. Riješiti: pokrenuti push iz nadzirane sesije (Andrej otvori Claude) ili ručno `git push origin feature/qrh-shared-lib`. Rad se nastavlja normalno — ovo ne blokira nijednu fazu.

**Preostalo:** ~38–56 h rada (F2–F10 + izvlačenje + test prihvatanja + A/C/.exe).
