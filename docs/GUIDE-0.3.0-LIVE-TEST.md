# PSE Riemann 0.3.0~rc1 — install and live test (for Andrej)

This guide is for you only and is not in the package. Follow it in order; every step has "what you should see" and a place for the result. Write the results into the table at the end (or just tell them to me).

## 0. What is in this release

- Every agent is a **PSE unit** (θ, Doctor, Laboratory, vote weights).
- **Mission agent** (talking about a mission), **"Awaiting your decision" in groups**, **SHARED_LIB talks like a person**, **translation on request**, **menu bar**, **two packages** (yours and the public one).

## 1. Installing your package

Package: `~/Desktop/PSE Riemann/pse-riemann-andrej_0.3.0~rc1_amd64.deb`. It replaces the old `pse-riemann` (0.2.0~rc2) — your results in "PSE Riemann rezultati" stay.

```bash
sudo apt install "$HOME/Desktop/PSE Riemann/pse-riemann-andrej_0.3.0~rc1_amd64.deb"
```

```bash
pse-riemann --selftest
```

**You should see:** at the end **✅ SVE PROLAZI**, "Izdanje: andrej", "PSE: svaki agent je jedinica … 16 jedinica", "sva 4 izvučena paketa se reprodukuju".

## 2. First start

1. Start it from the menu. **Menu bar** at the top: SHARED_LIB · Laboratory · Settings · Language · Help.
2. Top bar: the **"swarm N · θ …"** pill. Hover over it.
3. **Help → Guide** — the complete guide with pictures; at the end the "Your missions" addendum.

## 3. The live test, step by step

| # | Do | You should see |
|---|---|---|
| 1 | Settings: main = Claude, skeptic = DeepSeek (GGUF) | both pills green/blue |
| 2 | Chat, SHARED_LIB mode: "koje misije imam?" | sentences ("Imaš 3 misije…"), below them **▸ show where from** (SQL + rows) |
| 3 | Chat, math mode: ask a real question about mission 1 | an answer; a move of the chat unit in the Laboratory; **note how long it took** (with the reader) |
| 4 | Missions → **Talk about the mission** → select all → Start | the agent says what it sees and asks ≤ 3 questions; the skeptic attacks replies with numbers |
| 5 | Answer 2–3 times, then **Compose conclusion** | proposals as separate items in "Awaiting your decision", grouped under the mission |
| 6 | "Awaiting your decision": tick a few papers → Approve selected | the question "Approve N items?"; the Doctor's measures are not ticked in bulk |
| 7 | Right click on any text → **Translate to English** | the translation labelled "machine translation (model, date)"; Show original brings it back |
| 8 | Editor: open a note → right click → Translate | the translation in the preview; beside the file `….en-masinski.md` |
| 9 | **Laboratory** (first time in the session) | **3 s beep** + red banner; table of units |
| 10 | Laboratory: New test unit → Test move: unchecked | Doctor → a measure in "Awaiting your decision" (one by one) |
| 11 | SHARED_LIB → Swarm state | a table of all units |
| 12 | SHARED_LIB → Vote weights → Propose now | "Not enough data: n/200" (expected) |
| 13 | Language → English (restart) | the whole interface in English; content (missions) stays original |
| 14 | Work normally for **1 hour** | **note how many Doctor's measures arrived** |

## 4. Calibration — what matters most to me

θ is currently measured **literally per move** (agreement, rule 40). Note:

- **Doctor's measures in 1 hour of work:** ___ (which units, which triggers — see Laboratory → Doctor's journal)
- **Duration of one AI move with the reader:** cloud ___ s, GGUF ___ s
- Did the measures make sense? ___

If there are too many measures: the options are a moving average of θ (λ = 0.2) or a larger amplitude (see `docs/ZA-ANDREJA.md`).

## 5. The public package (check, optional)

`pse-riemann_0.3.0~rc1_amd64.deb` is for other people: empty missions, empty vault, "New mission…". Do not install it over yours (it would replace yours); to see it, try another computer or a virtual machine.

## 6. Results

| # | passed? | note |
|---|---|---|
| 1–14 | | |
| calibration | | |

When you are done: tell me the results and whether to push the local commits (list in `docs/ZA-ANDREJA.md`).
