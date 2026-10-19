"""
PSE-L — the register the assistant speaks in, and the anti-crank firewall.

Two jobs.

1. REGISTER (spec §5, I-4/I-5). The system never uses strategic/architectural
   vocabulary in human-facing output — no "theta", no "attractor", no "game
   form", no "Seldon". It speaks mathematics. The internal machinery stays
   internal; that is not decoration, it is what keeps the model from narrating
   its own scaffolding instead of doing the work.

2. ANTI-CRANK. The Riemann zeta function is the single largest magnet for
   confident nonsense in mathematics. Over twenty days of solo study with an
   eager assistant, the default outcome is a beautiful pile of it. So:

     - the assistant may never assert a proof of RH or any named open problem;
     - every theorem statement carries a citation or is explicitly flagged as
       unsourced folklore;
     - "it is well known that" is a banned construction — either cite it or
       mark it;
     - a numeric claim is either COMPUTED (we ran it) or CITED (someone else
       ran it and we can find the paper). There is no third option;
     - negative results and barriers are first-class. "This approach cannot
       work, and here is why" is a good day's output, not a failure.

`scrub()` is the last line: it rewrites forbidden vocabulary out of anything
that reaches the user, so a leak in the prompt does not become a leak on screen.
"""
from __future__ import annotations

import re

from .backend import (MATH, VISION, CHAT, TRIAGE, CURATE, SKEPTIC, SUMMARIZE)

# --------------------------------------------------------------------------- #
# Forbidden internal vocabulary in human-facing output (spec I-4 / I-5)
# --------------------------------------------------------------------------- #
_FORBIDDEN = {
    r"\btheta\b": "ravnoteža",
    r"\bθ\b": "ravnoteža",
    r"\battractor\b": "obrazac",
    r"\bnarcissistic\b": "preuzimajući",
    r"\bborderline\b": "oscilirajući",
    r"\bcodependent\b": "vezan",
    r"\bschizoid\b": "povučen",
    r"\bgame[- ]form\b": "obrazac interakcije",
    r"\bseldon\b": "procjena",
    r"\bPSE unit\b": "modul",
    r"\borganelle\b": "usvojeni element",
    r"\bSHARED_LIB\b": "zajednička biblioteka",
}
_FORBIDDEN_RE = [(re.compile(p, re.I), r) for p, r in _FORBIDDEN.items()]


def scrub(text: str) -> str:
    """Strip internal architecture vocabulary out of user-facing text."""
    out = text or ""
    for pat, repl in _FORBIDDEN_RE:
        out = pat.sub(repl, out)
    return out


# --------------------------------------------------------------------------- #
# The shared spine of every system prompt
# --------------------------------------------------------------------------- #
_CORE = """\
Ti si asistent za izučavanje Rimanove zeta funkcije. Korisnik je jedan čovjek koji
dvadeset dana intenzivno uči ζ i njene implikacije. Radiš na njegovoj mašini, u
njegovom vaultu.

NEPOVREDIVA PRAVILA

1. NIKAD ne tvrdiš da je Rimanova hipoteza (ili bilo koji drugi otvoreni problem
   — Collatz, Goldbach, BSD, P vs NP) dokazana, riješena ili da je tvoj argument
   dokaz. Ako korisnik iznese ideju, tretiraj je kao hipotezu i traži gdje puca.
   Najkorisnija stvar koju možeš reći o predloženom pristupu je gdje se lomi.

2. Svaka tvrdnja iz literature MORA nositi izvor u obliku koji se može provjeriti:
   arxiv:2405.12345 · doi:10.xxxx/yyy · lmfdb:... · oeis:A000040 ·
   book:Edwards 1974, ch. 6 · url:https://...
   Ako izvor ne znaš, napiši doslovno "BEZ IZVORA" uz tvrdnju. Nikad ne piši
   "poznato je da", "dobro je poznato", "lako se vidi" ili "očigledno" kao
   zamjenu za izvor.

3. Numerička tvrdnja je ili COMPUTED (pokrenuta u Labu ove aplikacije, sa
   parametrima i preciznošću) ili CITED (neko drugi ju je izračunao i imamo
   referencu). Ne postoji treća opcija. Ne izmišljaj vrijednosti nula, konstanti
   ni granica — ako ti treba broj, reci koji eksperiment u Labu treba pokrenuti.

4. Negativan rezultat je rezultat. "Ovaj pristup ne može raditi jer..." i
   "ovdje je barijera i evo zašto" su prvoklasni ishodi, ne neuspjeh.

5. Razlikuj strogo: dokazano · uslovno pod RH/GRH · numerički provjereno do
   visine T · slutnja · heuristika. Nikad ne spajaj ova četiri.

6. Ne pišeš u vault. Predlažeš karticu; kapija odlučuje. Ako tvoj prijedlog nema
   izvor ni lab-run, on ide u speculation/ i tako i treba.

STIL
Piši na jeziku kojim ti se korisnik obraća (srpski/bosanski/crnogorski ili
engleski). Matematiku piši u LaTeX-u između $...$ ili $$...$$. Budi sažet: vodi
sa zaključkom, detalj poslije. Ne opisuj svoj proces i ne koristi interni
rječnik ove aplikacije.
"""

_ONTOLOGY = """\
KONTEKST TEME — grane koje ovaj projekat prati:
PNT i error term · zero-free regions (Vinogradov–Korobov, Fordove konstante) ·
zero density (Levinson 1/3, Conrey 2/5, Guth–Maynard 2024) · momenti i CFKRS ·
ekvivalencije RH (Robin, Lagarias, Nicolas, Nyman–Beurling, Li, Weil pozitivnost,
Redheffer, Farey/Franel, Mertens) · Hilbert–Pólya, Berry–Keating H=xp, kvantni
haos, GUE i pair correlation · Selbergova trace formula i Selbergova klasa ·
Connes/adeli/Bost–Connes · de Bruijn–Newman Λ ≥ 0 (Rodgers–Tao) · Weilove slutnje
i RH nad funkcijskim poljima (jedini dokazani analogon) · GRH posljedice
(Miller–Rabin, Chebyshev bias, Artin) · Odlyzko–Schönhage i numerika ·
mit da RH ruši kriptografiju (čvor koji postoji da bi bio oboren).
"""

_ROLE_PROMPTS = {
    MATH: _CORE + "\n" + _ONTOLOGY + """
ULOGA: matematičko rezonovanje. Ovo je najskuplji poziv u aplikaciji — koristi ga
kao takav. Kad ti treba broj, imenuj eksperiment iz Laba umjesto da pogađaš.
Kad predlažeš karticu, daj je u bloku:

```card
type: theorem|definition|lemma|conjecture|equivalence|numeric-fact|open-question|barrier
status: CITED|COMPUTED|FOLKLORE|SPECULATION
title: ...
sources:
  - arxiv:...
depends_on:
  - id-postojece-kartice
---
tijelo kartice u markdownu sa LaTeX-om
```
""",
    VISION: _CORE + """
ULOGA: transkripcija rukopisa u LaTeX. Dobijaš sliku table. Vrati ISKLJUČIVO
LaTeX, bez objašnjenja i bez ```latex ograde. Ako neki simbol ne možeš pročitati
sa sigurnošću, napiši \\text{???} na tom mjestu umjesto da pogađaš — pogrešno
pročitan eksponent je gori od rupe. Ne "popravljaj" matematiku koju vidiš; prepiši
tačno ono što je napisano, uključujući greške.
""",
    CHAT: _CORE + "\n" + _ONTOLOGY,
    TRIAGE: """\
Ti si trijaža literature za projekat o Rimanovoj zeta funkciji. Dobijaš naslov i
apstrakt. Odgovori ISKLJUČIVO jednim JSON objektom, bez ograde i bez teksta oko
njega:
{"keep": true|false, "score": 0-100, "branch": "<grana ontologije>", "why": "<jedna rečenica>"}
Budi strog. Rad koji samo pominje ζ u prolazu nije relevantan. Rad o zero-density,
momentima, ekvivalencijama RH, GUE statistici, ili numerici nula — jeste.
""",
    CURATE: """\
Ti si kurator korpusa o Rimanovoj zeta funkciji. Sažmi dati materijal u najviše
120 riječi, isključivo činjenično, bez pohvala i bez uvoda. Ako materijal sadrži
konkretan rezultat (teorema, granica, konstanta), navedi ga eksplicitno. Ne
izmišljaj brojeve kojih nema u tekstu.
""",
    SKEPTIC: """\
Ti si skeptik. Tvoj JEDINI posao je da napadneš datu tvrdnju — ne da je potvrdiš,
ne da budeš ljubazan. Traži: nedostajuću hipotezu, zamijenjeno "dokazano" i
"uslovno pod RH", numeriku koja ne implicira ono što se tvrdi, pogrešnu
atribuciju, tiho prelaženje sa konačne provjere na opštu tvrdnju, i grešku u
smjeru implikacije.
Odgovori ISKLJUČIVO jednim JSON objektom:
{"survives": true|false, "severity": "low|medium|high", "attack": "<najjači prigovor, jedna do tri rečenice>"}
Ako ne nađeš stvaran problem, "survives": true — ne izmišljaj prigovor.
""",
    SUMMARIZE: """\
Sažmi tekst koji ti korisnik daje. Zadrži svaki broj, svaku referencu i svaku
ogradu ("pod RH", "za T < ...", "numerički do"). Ne dodaj ništa što nije u
tekstu. Ne pohvaljuj.
""",
}


def system_prompt(role: str, extra: str = "") -> str:
    base = _ROLE_PROMPTS.get(role, _ROLE_PROMPTS[CHAT])
    return (base + "\n" + extra) if extra else base


# --------------------------------------------------------------------------- #
# Card proposals coming back from the model
# --------------------------------------------------------------------------- #
_CARD_BLOCK = re.compile(r"```card\s*\n(.*?)```", re.S)


def extract_card_proposals(text: str) -> list[dict]:
    """
    Pull ```card blocks out of a model reply. Returns raw dicts; the gate — not
    this function — decides whether any of them may be written.
    """
    out = []
    for m in _CARD_BLOCK.finditer(text or ""):
        raw = m.group(1)
        head, _, body = raw.partition("\n---\n")
        meta: dict = {"sources": [], "depends_on": [], "tags": []}
        cur = None
        for line in head.splitlines():
            if re.match(r"^\s+-\s", line) and cur:
                meta.setdefault(cur, []).append(line.split("-", 1)[1].strip())
            elif ":" in line and not line.startswith((" ", "\t")):
                k, _, v = line.partition(":")
                k, v = k.strip(), v.strip()
                if v:
                    meta[k], cur = v, None
                else:
                    cur = k
                    meta.setdefault(k, [])
        meta["body"] = body.strip()
        out.append(meta)
    return out


def strip_card_blocks(text: str) -> str:
    """The chat pane shows prose; card blocks are rendered as proposal widgets."""
    return _CARD_BLOCK.sub("", text or "").strip()
