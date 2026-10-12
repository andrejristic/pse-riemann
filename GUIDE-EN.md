# PSE Riemann — guide

Ordered by importance. The Serbian guide ([VODIC-SR.md](VODIC-SR.md)) is the
primary one; this is the same content, condensed.

---

## 1. Run

```bash
cd ~/Desktop/PSE/PSE\ Riemann/app
./setup.sh                 # ONCE, at home, with internet — creates app/.venv
./run.sh                   # GUI
./run.sh --selftest        # numerics, gate, guardian, journal — headless
./run.sh --lab explicit    # run one experiment from the terminal
./run.sh --harvest         # one ingest cycle
./run.sh --briefing        # morning briefing
```

`setup.sh` creates `app/.venv` and installs PySide6-Essentials, mpmath, numpy
and matplotlib into it. Nothing system-wide: Mint's Python is PEP-668 locked, so
a venv is the only correct route; deleting `app/.venv` undoes everything.

The app still uses **no HTTP library** — networking is stdlib through one gated
function, so TLS pinning and the allowlist cannot be bypassed by a dependency.

---

## 2. ⚠ Do this before you travel

0. `./setup.sh` — once, at home, with internet.
1. Launch **on a network you trust** (home).
2. Wizard → enter keys → **Test** each provider.
3. Corpus → **⬇ Skupi** (harvest), let one cycle run.
4. Guardian → **Test mreže** (preflight).

The app pins each server's public keys on **first contact** and afterwards
refuses to talk to a server that cannot show them. That is the defence against
interception on someone else's WiFi — and it is worth exactly as much as the
network you were on when the pin was learned. Pin at home, not in a hotel.

While you are in the Guardian tab, read the host findings: if `ufw` is off or
something is listening beyond loopback, the exact command is printed there.

---

## 3. The daily rule

**At least one `COMPUTED` result per day.** Reading without computing does not
count. The status bar measures it.

Morning: the app opens on **Plan** — yesterday, open questions, what the plan
says, what needs attention. Evening: Editor → daily note.

---

## 4. Lab — the only truth the app produces itself

Twelve experiments in pedagogical order. `selftest` first (if it fails, trust
nothing else). Then `z_curve` → `zeros` → `counting` → `gram` → **`explicit`**
(primes emerging from zeros — the single best demo) → `prime_counting` → `gue`
→ `robin` / `mertens` (RH as a statement about integers) → `s_of_t` → `strip`.

Every run writes a `COMPUTED` card carrying its parameters, numbers, plot, the
**sha256 of the script that produced it**, and the mpmath version. Months later
you can rerun `vault/lab/<run_id>/script.py` and get the same number. The gate
refuses a `COMPUTED` card without that — an unverifiable number in a knowledge
base is worse than none, because later it looks identical to a verified one.

---

## 5. The gate

One write path. `COMPUTED` needs a lab run + script hash; `CITED` needs a
resolvable source (`arxiv:` / `doi:` / `oeis:` / `book:… ch. 6` / …);
`FOLKLORE` is admitted but marked and can never support a verified card;
`SPECULATION` lives in `speculation/`, never in `knowledge/`; `SUSPECT` carries
the skeptic's objection in its body; `REFUTED` is **never deleted** — a negative
result is a result.

**Anti-crank.** A card claiming a proof of RH (or Collatz, Goldbach, BSD, P vs
NP) is refused, whoever wrote it. The filter is context-aware, so true
statements pass: *"Weil proved the RH analogue over function fields"* ✅,
*"a proof of RH would not break RSA"* ✅, *"assuming RH, the error in π(x) is
O(√x log x)"* ✅, *"I have proved the Riemann hypothesis"* ⛔.

---

## 6. Chat (right 30%)

Input grows with your text to **half the panel height**, then scrolls. Context
is **explicit** — what is in the tray is what the model sees, no hidden
retrieval. The model **cannot write**: it proposes a card and you see the gate's
verdict *before* you click.

---

## 7. Routing — why this costs almost nothing

`math` and `vision` → the strong model. `triage`, `curate`, `summarize` → free
tiers (Groq/Mistral/Gemini). `skeptic` → deliberately a **different** provider
from the one that wrote the card; a model grading its own work is not a check.

The daily cap is a hard stop, not a warning (default $5). When it is reached,
paid calls stop and free providers keep working.

---

## 8. Corpus

Three filters, increasing cost: coarse keyword gate (free) → model triage (one
cheap call) → promotion through the gate. Raw material lands in `inbox/`, which
is a **cheap signal, not the corpus**.

**📖 Read paper** (arXiv only) pulls ar5iv HTML — no PDF parser — and the strong
model extracts 2–6 cards, each carrying the arXiv id as its source.
**⚔ Skeptic** attacks a card; a landed hit flips it to `SUSPECT` and writes the
objection into the card, so the doubt travels with the claim.

All sources are keyless: arXiv, ar5iv, **LMFDB**, OEIS, OpenAlex, Crossref,
Wikipedia, zbMATH, MathOverflow, Numdam, Odlyzko, Tao's blog. LMFDB supplies
~32-digit zeros; `cross_check_zeros()` compares them against our mpmath — two
independent sources agreeing is evidence, one is just a number.

---

## 9. Whiteboard

Strokes are **always** saved as SVG + PNG and embedded in a markdown note,
with or without transcription. Vector never fails, needs no model, no network,
and invents no exponents. *Transcribe* sends the image to a vision model and the
LaTeX arrives as a **proposal** beside your drawing. An unreadable symbol comes
back as `\text{???}` — a hole beats a misread exponent.

---

## 10. Guardian

Every outbound byte passes one function: https only · default-deny allowlist ·
quarantine check · rate limit · **keys only to model APIs** (key material headed
to a literature host blocks the whole request) · hardened TLS with **SPKI pinning**
(whole chain on Python 3.13+; on this host's 3.12 the leaf key plus the issuer
identity, so a leaf rotation passes as `rotated` while a hotel proxy — signing
with its own CA — fails both checks) · manual redirects re-validated from step 1 · size/timeout/zip-bomb caps ·
seven anomaly axes scored per host.

Captive portals are detected rather than walked into: they either fail the pin
(being a MITM by construction) or answer an API request with HTML. Both are
refused **before** a key is sent.

**What it does not do:** secure your laptop. It secures this application's
surface and tells you how the machine looks to the network. For the rest: `ufw`,
a VPN, and don't leave the machine unattended.

---

## 11. Balance (status bar)

0–100: how much of the work is directed at **other** (literature, model output,
scraping) versus **your own** (Lab, your notes, your derivations). Above 35 you
are consuming, not deriving; below 25 speculation is outrunning verification;
σ below 0.01 means it stopped learning. Persisted across launches.

---

## 12. Layout

`app/` code · `vault/` everything of yours (`knowledge/ speculation/ sources/
notes/ daily/ lab/ inbox/ media/ .state/`) · `PLAN.md` · `OPEN_QUESTIONS.md`.
Keys live **outside** the vault in `~/.config/pse-riemann/secrets.json` (0600).
The vault is plain markdown — it works without this app, and opens in Obsidian.

`~/Desktop/123/PSE_MASTER_ARCHITECTURE.txt` is read-only reference, never touched.

---

## 13. UI size and panel layout

This desktop runs at `Xft.dpi 240` (2.5×) plus a 1.25 text factor, which Qt
multiplies into an unusable window. The app therefore **ignores desktop scaling
entirely** and applies only its own factor: `ui_scale = 1.0` looks like a plain
100% desktop whatever the system says.

`Ctrl +` / `Ctrl -` resize text live; `Ctrl 0` resets. For the whole UI:
`Ctrl+K` → "Prikaz — veličina interfejsa" (restart), or `./run.sh --scale 1.25`.

Every panel border is draggable (7 px, highlights on hover), horizontally and
vertically, and window + splitter sizes persist across launches.
`Ctrl+K` → "Prikaz — resetuj raspored panela" starts over.

---

## 14. Shortcuts

`Ctrl+K` command palette · `Ctrl+S` save · `Ctrl+1/2/3` Plan/Lab/Corpus ·
`Ctrl +/-/0` text size · `Enter` send, `Shift+Enter` newline.

---

## 15. What this is not

Not a theorem prover (no formal checking — that would need Lean). Not a complete
LaTeX renderer (matplotlib mathtext is a large subset; what it cannot parse is
shown as source, never dropped silently). Not endpoint security. It does not
know whether RH is true and will not pretend to.
