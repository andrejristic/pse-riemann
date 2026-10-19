"""
The zeta ontology — the map the scraper walks.

Without this file the crawler is a hoover: twenty days later you have four
thousand PDFs and no knowledge. With it, every fetch is attached to a branch of
the subject, the curator can score relevance against something concrete, and
the vault grows along a shape you can actually study.

Each branch carries: the queries that find it, the keywords that recognise it,
and a one-line statement of *why it is in the map at all*. That last field is
what you read on day three when you have forgotten why you cared.

The list is deliberately opinionated. `crypto_myth` is in here not because it
is a research direction but because it is the most common false belief about
RH, and a node that exists to be refuted is worth more than one that is absent.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Branch:
    key: str
    title: str
    why: str
    queries: list = field(default_factory=list)
    keywords: list = field(default_factory=list)
    weight: float = 1.0          # relative crawl budget


BRANCHES: list[Branch] = [
    Branch("pnt_error", "PNT i error term",
           "Osnovna veza: greška u brojanju primova JE tvrdnja o nulama.",
           ["prime number theorem error term", "psi(x) explicit formula"],
           ["prime number theorem", "error term", "chebyshev psi",
            "explicit formula", "von mangoldt"], 1.0),
    Branch("zero_free", "Zero-free regions",
           "Sve bezuslovno poznato o primovima dolazi iz zero-free regiona.",
           ["zeta zero-free region", "Vinogradov Korobov zero free"],
           ["zero-free region", "vinogradov", "korobov", "ford constant"], 1.0),
    Branch("zero_density", "Zero density i Guth–Maynard",
           "Najveći pomak u decenijama (2024) — gdje je granica danas.",
           ["zeta zero density estimate", "Guth Maynard zero density"],
           ["zero density", "density estimate", "guth", "maynard",
            "large values dirichlet"], 1.4),
    Branch("moments", "Momenti i CFKRS",
           "Momenti su most ka slučajnim matricama i ka Lindelöfu.",
           ["moments of the Riemann zeta function", "CFKRS moment conjecture"],
           ["moments", "keating snaith", "cfkrs", "lindelof"], 1.0),
    Branch("equivalences", "Ekvivalencije RH",
           "RH prevedena u tvrdnje koje se mogu računati sa cijelim brojevima.",
           ["Robin criterion Riemann hypothesis equivalent",
            "Nyman Beurling criterion", "Li criterion positivity"],
           ["robin", "lagarias", "nicolas", "nyman", "beurling", "li criterion",
            "redheffer", "farey", "franel", "mertens function",
            "equivalent to the riemann hypothesis"], 1.3),
    Branch("rmt", "Slučajne matrice, GUE, kvantni haos",
           "Zašto se uopšte vjeruje u Hilbert–Pólya.",
           ["Montgomery pair correlation zeta GUE",
            "Berry Keating xp quantum chaos zeta"],
           ["pair correlation", "gue", "random matrix", "montgomery",
            "odlyzko", "berry", "keating", "quantum chaos",
            "hilbert-polya", "hilbert polya"], 1.3),
    Branch("selberg", "Selbergova trace formula i Selbergova klasa",
           "Analogija spektra: gdje 'trace formula' zaista radi.",
           ["Selberg trace formula zeta", "Selberg class L-functions"],
           ["selberg", "trace formula", "selberg class"], 0.9),
    Branch("connes", "Connes, adeli, Bost–Connes",
           "Nekomutativna geometrija kao kandidat za spektralnu interpretaciju.",
           ["Connes trace formula Riemann adeles",
            "Bost-Connes system zeta"],
           ["connes", "adele", "noncommutative", "bost-connes"], 0.8),
    Branch("dbn", "de Bruijn–Newman Λ ≥ 0",
           "Rodgers–Tao 2018: RH je, ako je tačna, 'jedva' tačna.",
           ["de Bruijn-Newman constant", "Rodgers Tao Lambda nonnegative"],
           ["de bruijn", "newman constant", "rodgers", "tao", "lambda"], 1.0),
    Branch("function_fields", "RH nad funkcijskim poljima (Weil)",
           "JEDINI slučaj gdje je analogon RH dokazan — najvrednija grana za "
           "intuiciju o tome šta bi dokaz uopšte trebalo da bude.",
           ["Weil conjectures Riemann hypothesis function fields",
            "Deligne Weil II"],
           ["weil conjecture", "function field", "deligne", "frobenius",
            "curves over finite fields"], 1.2),
    Branch("grh", "GRH i njene posljedice",
           "Šta se sve mijenja ako je RH tačna za sve Dirichletove L-funkcije.",
           ["generalized Riemann hypothesis consequences",
            "GRH Miller-Rabin primality"],
           ["generalized riemann hypothesis", "grh", "dirichlet l-function",
            "chebyshev bias", "artin conjecture", "miller-rabin"], 1.0),
    Branch("numerics", "Numerika nula (Odlyzko–Schönhage)",
           "Kako se uopšte računaju milijarde nula i dokle se stiglo.",
           ["Odlyzko Schonhage algorithm zeta zeros computation",
            "verification Riemann hypothesis height"],
           ["odlyzko", "schonhage", "riemann-siegel", "turing method",
            "computation of zeros", "gram point", "rosser rule",
            "lehmer pair"], 1.1),
    Branch("crypto_myth", "Mit: RH i kriptografija",
           "Najčešća pogrešna predstava o RH. Ovaj čvor postoji da bi bio "
           "oboren — dokaz RH ne razbija RSA.",
           ["does the Riemann hypothesis break RSA cryptography"],
           ["rsa", "cryptography", "factoring", "breaks encryption"], 0.4),
]

BY_KEY = {b.key: b for b in BRANCHES}


def branch_scores(text: str) -> dict:
    """Keyword overlap per branch. Cheap prefilter before any model sees it."""
    low = (text or "").lower()
    out = {}
    for b in BRANCHES:
        hits = sum(1 for k in b.keywords if k in low)
        if hits:
            out[b.key] = hits * b.weight
    return out


def best_branch(text: str) -> tuple[str, float]:
    sc = branch_scores(text)
    if not sc:
        return "", 0.0
    k = max(sc, key=lambda x: sc[x])
    return k, sc[k]


def is_zeta_relevant(text: str) -> bool:
    """
    Coarse gate before spending a model call. A paper that never mentions zeta,
    L-functions, or primes is not worth triaging.
    """
    low = (text or "").lower()
    anchors = ("zeta", "l-function", "l function", "riemann", "prime",
               "dirichlet", "critical line", "critical strip")
    return any(a in low for a in anchors)


def crawl_plan(rounds: int = 1) -> list[tuple[str, str]]:
    """
    (branch_key, query) pairs, ordered so heavier branches come first and every
    branch gets touched before any branch is revisited.
    """
    plan = []
    for r in range(rounds):
        for b in sorted(BRANCHES, key=lambda x: -x.weight):
            if r < len(b.queries):
                plan.append((b.key, b.queries[r]))
    return plan
