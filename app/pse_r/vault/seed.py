"""
Seeding the vault — the spine the graph hangs on.

On first run the vault gets one note per ontology branch, with a stable id
(`tema-<branch>`), plus a study plan and an open-questions file. Everything the
app writes afterwards links back into this spine: a lab run links to the branch
it belongs to, a promoted paper links to the branch it was classified into. Two
weeks later the graph tab shows the shape of what you actually studied instead
of a cloud of orphans.

These notes are FOLKLORE by design and say so: they are orientation, written by
the app, carrying no citation. Nothing verified may depend on them. They are a
map, and a map is not a claim.
"""
from __future__ import annotations

from .. import config
from ..core import journal as J
from ..ingest.topics import BRANCHES
from .card import Card, FOLKLORE
from .gate import gate

PLAN_FILE = "PLAN.md"
QUESTIONS_FILE = "OPEN_QUESTIONS.md"


def topic_id(branch_key: str) -> str:
    return f"tema-{branch_key}"


def seed_topics(force: bool = False) -> dict:
    """One note per branch. Idempotent: existing notes are left alone."""
    made = skipped = failed = 0
    reasons = []
    for b in BRANCHES:
        cid = topic_id(b.key)
        if gate().find(cid) and not force:
            skipped += 1
            continue
        body = [
            f"> Orijentaciona mapa grane, bez izvora. Ne oslanjaj provjerenu "
            f"karticu na ovu — ona je mapa, ne tvrdnja.", "",
            f"**Zašto je ova grana u mapi.** {b.why}", "",
            "**Ključni pojmovi.** " + ", ".join(f"`{k}`" for k in b.keywords[:12]),
            "", "**Upiti kojima je scraper prati.**",
        ] + [f"- {q}" for q in b.queries] + [
            "", "## Šta znam", "", "_(popuni kako učiš)_", "",
            "## Otvorena pitanja", "", "_(prebaci u OPEN_QUESTIONS.md ono što te "
            "stvarno muči)_", "",
        ]
        card = Card(id=cid, title=f"Tema: {b.title}", type="note",
                    status=FOLKLORE, author="seed",
                    tags=["tema", b.key], body="\n".join(body))
        v = gate().submit(card, actor="seed")
        if v.ok:
            made += 1
        else:
            failed += 1
            reasons.append(v.reason[:100])
    J.log(J.SYSTEM, "seed", {"topics_made": made, "skipped": skipped,
                             "failed": failed, "reasons": reasons[:3]})
    return {"made": made, "skipped": skipped, "failed": failed,
            "reasons": reasons}


PLAN_TEMPLATE = """# Plan — 20 dana sa Rimanovom zetom

Kičma. Mijenjaj je slobodno; aplikacija je samo čita da bi znala gdje si.
Format reda: `- [ ] D<dan> · <tema> · <lab eksperiment>`

## Nedjelja 1 — mašinerija
- [ ] D1 · Šta je ζ, Ojlerov proizvod, analitičko produženje · `selftest`, `z_curve`
- [ ] D2 · Funkcionalna jednačina i kritična traka · `strip`
- [ ] D3 · Hardy Z, θ(t), kako se nule uopšte nalaze · `zeros`
- [ ] D4 · N(T), S(T), Turingova metoda · `counting`, `s_of_t`
- [ ] D5 · Gramove tačke, Gramov zakon, Rosser · `gram`
- [ ] D6 · **Eksplicitna formula** — primovi iz nula · `explicit`
- [ ] D7 · π(x), li(x), R(x), Skewes · `prime_counting`

## Nedjelja 2 — zašto je važna
- [ ] D8 · PNT i error term: RH kao tvrdnja o grešci
- [ ] D9 · Zero-free regioni: sve bezuslovno poznato
- [ ] D10 · Zero density i Guth–Maynard (2024)
- [ ] D11 · Ekvivalencije: Robin, Nicolas, Lagarias · `robin`
- [ ] D12 · Mertens, Nyman–Beurling, Li kriterijum · `mertens`
- [ ] D13 · Momenti i CFKRS
- [ ] D14 · Pregled nedjelje: šta je dokazano vs uslovno

## Nedjelja 3 — spektralna slika
- [ ] D15 · Montgomery, pair correlation, GUE · `gue`
- [ ] D16 · Hilbert–Pólya, Berry–Keating H=xp
- [ ] D17 · Selbergova trace formula i Selbergova klasa
- [ ] D18 · **RH nad funkcijskim poljima** — jedini dokazani analogon
- [ ] D19 · Connes, adeli; de Bruijn–Newman Λ ≥ 0
- [ ] D20 · Sinteza: mapa barijera — zašto svaki poznati pristup pada

## Pravila za sebe
1. Svaki dan bar jedan `COMPUTED` rezultat. Čitanje bez računanja se ne broji.
2. Svaka tvrdnja koju zapišeš dobija izvor ili oznaku BEZ IZVORA. Bez izuzetka.
3. Kad ti se učini da si nešto dokazao — to je znak da nešto ne razumiješ.
   Zapiši u `speculation/` i idi dalje.
4. Negativan rezultat i barijera su rezultat. Zapiši ih kao `barrier` kartice.
"""

QUESTIONS_TEMPLATE = """# Otvorena pitanja

Živi red. Gore ide ono što te trenutno najviše muči.
Kad pitanje dobije odgovor sa izvorom ili lab-runom — napravi karticu i obriši red.

- [ ] Zašto Gramov zakon pada, i da li kršenja imaju strukturu?
- [ ] Koliko tačno S(T) mora narasti da bi RH pala, i zašto je to nedostižno numerički?
- [ ] Šta konkretno Weilov dokaz nad funkcijskim poljima koristi, a što u
      klasičnom slučaju nedostaje?
- [ ] Zašto zero-density teoreme daju bezuslovne rezultate o primovima?
- [ ] Da li je odbijanje nula (GUE) posljedica nečega elementarnog?
"""


def seed_files(force: bool = False) -> dict:
    made = []
    for name, text in ((PLAN_FILE, PLAN_TEMPLATE),
                       (QUESTIONS_FILE, QUESTIONS_TEMPLATE)):
        p = config.VAULT / name
        if p.exists() and not force:
            continue
        p.write_text(text, encoding="utf-8")
        made.append(name)
    if made:
        J.log(J.SYSTEM, "seed", {"files": made})
    return {"files": made}


def seed_all(force: bool = False) -> dict:
    out = {"topics": seed_topics(force), "files": seed_files(force)}
    return out


def is_seeded() -> bool:
    return gate().find(topic_id(BRANCHES[0].key)) is not None
