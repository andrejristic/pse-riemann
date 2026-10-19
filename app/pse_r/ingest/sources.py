"""
Source clients. Every one of them keyless, every one of them through the gate.

Each client returns a list of `Item` — a normalised record with a resolvable
source reference (`arxiv:2405.12345`, `doi:...`, `openalex:W...`) already
attached, because a record that cannot be cited is not worth storing.

Politeness is not optional here and is not left to the caller: the rate limits
live in `guardian/policy.py` and are enforced by the egress gate, arXiv gets
its one-request-per-three-seconds, and Crossref/OpenAlex get a `mailto` so we
sit in the polite pool. On a shared hotel connection, being a well-behaved
client is also self-defence — a burst looks exactly like the scan signature the
Guardian is built to notice.
"""
from __future__ import annotations

import json
import re
import urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Optional

from ..guardian import content as C
from ..guardian.egress import EgressBlocked, egress
from ..guardian import secrets as SEC


@dataclass
class Item:
    source_ref: str                  # arxiv:... | doi:... | openalex:W... | ...
    title: str
    abstract: str = ""
    authors: list = field(default_factory=list)
    year: str = ""
    url: str = ""
    venue: str = ""
    origin: str = ""                 # which client produced it
    extra: dict = field(default_factory=dict)
    injection_hits: list = field(default_factory=list)

    def key(self) -> str:
        """Dedup key: prefer the identifier, fall back to a normalised title."""
        if self.source_ref:
            return self.source_ref.lower().split("v")[0] \
                if self.source_ref.startswith("arxiv:") else self.source_ref.lower()
        return re.sub(r"[^a-z0-9]+", "", (self.title or "").lower())[:80]

    def text(self) -> str:
        return f"{self.title}\n\n{self.abstract}"


def _email() -> str:
    return SEC.store().get("CONTACT_EMAIL") or ""


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def _scan(it: Item) -> Item:
    """Every field that came off the network gets the injection scan."""
    hits = C.scan_injection(it.text())
    it.injection_hits = hits
    it.title = _clean(it.title)[:400]
    it.abstract = _clean(it.abstract)[:8000]
    return it


# --------------------------------------------------------------------------- #
# arXiv
# --------------------------------------------------------------------------- #
_ATOM = {"a": "http://www.w3.org/2005/Atom"}


def arxiv_search(query: str, max_results: int = 25,
                 category: str = "math.NT") -> list[Item]:
    q = f'all:"{query}"'
    if category:
        q = f"cat:{category} AND {q}"
    url = ("https://export.arxiv.org/api/query?" + urllib.parse.urlencode(
        {"search_query": q, "start": 0, "max_results": max_results,
         "sortBy": "relevance", "sortOrder": "descending"}))
    r = egress().get(url, max_bytes=4_000_000)
    return _parse_arxiv(r.text)


def arxiv_recent(category: str = "math.NT", max_results: int = 40) -> list[Item]:
    url = ("https://export.arxiv.org/api/query?" + urllib.parse.urlencode(
        {"search_query": f"cat:{category}", "start": 0,
         "max_results": max_results, "sortBy": "submittedDate",
         "sortOrder": "descending"}))
    r = egress().get(url, max_bytes=4_000_000)
    return _parse_arxiv(r.text)


def _parse_arxiv(xml_text: str) -> list[Item]:
    out: list[Item] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return out
    for e in root.findall("a:entry", _ATOM):
        idu = (e.findtext("a:id", "", _ATOM) or "").strip()
        m = re.search(r"abs/([^v]+)(v\d+)?$", idu)
        aid = m.group(1) if m else ""
        if not aid:
            continue
        doi = e.findtext("{http://arxiv.org/schemas/atom}doi", "", ) or ""
        it = Item(source_ref=f"arxiv:{aid}",
                  title=e.findtext("a:title", "", _ATOM),
                  abstract=e.findtext("a:summary", "", _ATOM),
                  authors=[a.findtext("a:name", "", _ATOM)
                           for a in e.findall("a:author", _ATOM)][:12],
                  year=(e.findtext("a:published", "", _ATOM) or "")[:4],
                  url=idu, origin="arxiv",
                  extra={"doi": doi,
                         "ar5iv": f"https://ar5iv.org/abs/{aid}",
                         "categories": [c.get("term") for c in
                                        e.findall("a:category", _ATOM)]})
        out.append(_scan(it))
    return out


def ar5iv_fulltext(arxiv_id: str, max_chars: int = 200_000) -> C.ContentReport:
    """HTML rendering of a paper — readable, and no PDF parser needed."""
    aid = re.sub(r"[^0-9A-Za-z./\-]", "", arxiv_id.replace("arxiv:", ""))
    r = egress().get(f"https://ar5iv.org/abs/{aid}", max_bytes=8_000_000)
    rep = C.prepare(r.text, f"arxiv:{aid}", is_html=True)
    rep.text = rep.text[:max_chars]
    return rep


# --------------------------------------------------------------------------- #
# OpenAlex — citation graph, keyless (mailto = polite pool)
# --------------------------------------------------------------------------- #
def openalex_search(query: str, per_page: int = 25) -> list[Item]:
    params = {"search": query, "per-page": per_page,
              "filter": "type:article"}
    if _email():
        params["mailto"] = _email()
    r = egress().get("https://api.openalex.org/works?" +
                     urllib.parse.urlencode(params), max_bytes=6_000_000)
    d = r.json()
    out = []
    for w in d.get("results", []):
        wid = (w.get("id") or "").rsplit("/", 1)[-1]
        doi = (w.get("doi") or "").replace("https://doi.org/", "")
        ref = f"doi:{doi}" if doi else (f"openalex:{wid}" if wid else "")
        if not ref:
            continue
        inv = w.get("abstract_inverted_index") or {}
        abstract = _deinvert(inv) if inv else ""
        out.append(_scan(Item(
            source_ref=ref, title=w.get("display_name") or "",
            abstract=abstract,
            authors=[a.get("author", {}).get("display_name", "")
                     for a in (w.get("authorships") or [])][:12],
            year=str(w.get("publication_year") or ""),
            url=w.get("doi") or w.get("id") or "",
            venue=((w.get("primary_location") or {}).get("source") or {}
                   ).get("display_name", "") or "",
            origin="openalex",
            extra={"cited_by": w.get("cited_by_count", 0),
                   "openalex": wid})))
    return out


def _deinvert(inv: dict) -> str:
    pos = {}
    for word, idxs in inv.items():
        for i in idxs:
            pos[i] = word
    return " ".join(pos[k] for k in sorted(pos))[:8000]


# --------------------------------------------------------------------------- #
# Crossref — DOI metadata, keyless
# --------------------------------------------------------------------------- #
def crossref_search(query: str, rows: int = 20) -> list[Item]:
    params = {"query": query, "rows": rows, "select":
              "DOI,title,abstract,author,issued,container-title,URL"}
    if _email():
        params["mailto"] = _email()
    r = egress().get("https://api.crossref.org/works?" +
                     urllib.parse.urlencode(params), max_bytes=6_000_000)
    d = r.json()
    out = []
    for w in (d.get("message", {}).get("items") or []):
        doi = w.get("DOI")
        if not doi:
            continue
        title = " ".join(w.get("title") or [])
        abstract = re.sub(r"<[^>]+>", " ", w.get("abstract") or "")
        yr = ""
        try:
            yr = str((w.get("issued", {}).get("date-parts") or [[""]])[0][0])
        except (IndexError, TypeError):
            pass
        out.append(_scan(Item(
            source_ref=f"doi:{doi}", title=title, abstract=abstract,
            authors=[f"{a.get('given','')} {a.get('family','')}".strip()
                     for a in (w.get("author") or [])][:12],
            year=yr, url=w.get("URL", ""),
            venue=" ".join(w.get("container-title") or []),
            origin="crossref")))
    return out


# --------------------------------------------------------------------------- #
# zbMATH Open — reviews, keyless (open subset)
# --------------------------------------------------------------------------- #
def zbmath_search(query: str, results: int = 15) -> list[Item]:
    url = ("https://api.zbmath.org/v1/document/_search?" +
           urllib.parse.urlencode({"search_string": query,
                                   "results_per_page": results, "page": 1}))
    try:
        r = egress().get(url, max_bytes=6_000_000)
        d = r.json()
    except (EgressBlocked, json.JSONDecodeError, ValueError):
        return []
    out = []
    for w in (d.get("result") or []):
        title = ((w.get("title") or {}).get("title")) or ""
        doi = (w.get("links") or [{}])
        ref = ""
        for l in (w.get("links") or []):
            if (l.get("type") or "").lower() == "doi" and l.get("identifier"):
                ref = f"doi:{l['identifier']}"
                break
        if not ref:
            zid = w.get("id")
            ref = f"url:https://zbmath.org/?q=an:{zid}" if zid else ""
        if not ref:
            continue
        out.append(_scan(Item(
            source_ref=ref, title=title,
            abstract=(w.get("editorial_contributions") or [{}])[0].get("text", "")
            if w.get("editorial_contributions") else "",
            authors=[a.get("name", "") for a in (w.get("contributors", {})
                                                 .get("authors") or [])][:12],
            year=str(w.get("year") or ""), origin="zbmath")))
    return out


# --------------------------------------------------------------------------- #
# MathOverflow / Math.SE — keyless (optional free key raises the quota)
# --------------------------------------------------------------------------- #
def stackexchange_search(query: str, site: str = "mathoverflow",
                         pagesize: int = 15) -> list[Item]:
    params = {"order": "desc", "sort": "relevance", "q": query,
              "site": site, "filter": "withbody", "pagesize": pagesize}
    key = SEC.store().get("STACKEXCHANGE_KEY")
    if key:
        params["key"] = key
    r = egress().get("https://api.stackexchange.com/2.3/search/advanced?" +
                     urllib.parse.urlencode(params), max_bytes=4_000_000)
    d = r.json()
    out = []
    for q in (d.get("items") or []):
        qid = q.get("question_id")
        if not qid:
            continue
        out.append(_scan(Item(
            source_ref=f"mathoverflow:{qid}" if site == "mathoverflow"
            else f"url:{q.get('link','')}",
            title=q.get("title") or "",
            abstract=C.sanitize_html(q.get("body") or "")[:4000],
            url=q.get("link", ""), origin=site,
            extra={"score": q.get("score", 0),
                   "answers": q.get("answer_count", 0),
                   "accepted": bool(q.get("is_answered"))})))
    return out


# --------------------------------------------------------------------------- #
# OEIS
# --------------------------------------------------------------------------- #
def oeis_search(query: str, limit: int = 10) -> list[Item]:
    r = egress().get("https://oeis.org/search?" + urllib.parse.urlencode(
        {"q": query, "fmt": "json", "start": 0}), max_bytes=3_000_000)
    try:
        d = r.json()
    except (json.JSONDecodeError, ValueError):
        return []
    results = d if isinstance(d, list) else (d.get("results") or [])
    out = []
    for s in (results or [])[:limit]:
        num = s.get("number")
        if num is None:
            continue
        aid = f"A{int(num):06d}"
        out.append(_scan(Item(
            source_ref=f"oeis:{aid}", title=s.get("name", ""),
            abstract=" ".join(s.get("comment", []) or [])[:3000],
            url=f"https://oeis.org/{aid}", origin="oeis",
            extra={"data": s.get("data", "")})))
    return out


# --------------------------------------------------------------------------- #
# Wikipedia — orientation only, never a citable source for a theorem
# --------------------------------------------------------------------------- #
def wikipedia_extract(title: str) -> Optional[Item]:
    params = {"action": "query", "prop": "extracts", "explaintext": 1,
              "redirects": 1, "format": "json", "titles": title}
    r = egress().get("https://en.wikipedia.org/w/api.php?" +
                     urllib.parse.urlencode(params), max_bytes=4_000_000)
    d = r.json()
    pages = (d.get("query") or {}).get("pages") or {}
    for _, pg in pages.items():
        if "extract" not in pg:
            continue
        return _scan(Item(
            source_ref=f"wikipedia:{pg.get('title','').replace(' ', '_')}",
            title=pg.get("title", ""), abstract=pg["extract"][:20000],
            url=f"https://en.wikipedia.org/wiki/"
                f"{urllib.parse.quote(pg.get('title','').replace(' ', '_'))}",
            origin="wikipedia"))
    return None


# --------------------------------------------------------------------------- #
# Tao's blog — RSS
# --------------------------------------------------------------------------- #
def tao_blog(limit: int = 15) -> list[Item]:
    r = egress().get("https://terrytao.wordpress.com/feed/", max_bytes=4_000_000)
    out = []
    try:
        root = ET.fromstring(r.text)
    except ET.ParseError:
        return out
    for item in root.iter("item"):
        link = (item.findtext("link") or "").strip()
        if not link:
            continue
        out.append(_scan(Item(
            source_ref=f"url:{link}",
            title=item.findtext("title") or "",
            abstract=C.sanitize_html(item.findtext("description") or "")[:4000],
            url=link, origin="tao",
            extra={"date": item.findtext("pubDate") or ""})))
        if len(out) >= limit:
            break
    return out


# --------------------------------------------------------------------------- #
# LMFDB — real zeros and L-function data
# --------------------------------------------------------------------------- #
def lmfdb_zeta_zeros(t_start: float = 0.0, limit: int = 100
                     ) -> list[tuple[int, str]]:
    """
    Zeros of zeta from LMFDB, as (index, decimal string) with ~32 digits.

    This is the single most valuable thing an external database does for this
    project: an INDEPENDENT high-precision list to check our own mpmath run
    against. Two sources agreeing is evidence; one source is just a number.

    Returns the digits as strings, not floats — float() would silently throw
    away two thirds of the precision LMFDB is giving us, which defeats the
    entire point of asking them.

    On any failure this returns [] and the caller falls back to computing the
    zeros locally. It never substitutes one source's numbers for another's.
    """
    url = ("https://www.lmfdb.org/zeros/zeta/list?" + urllib.parse.urlencode(
        {"limit": min(int(limit), 1000), "t": t_start}))
    try:
        r = egress().get(url, max_bytes=4_000_000)
    except EgressBlocked:
        return []
    if r.status != 200 or "<html" in r.text[:200].lower():
        return []
    out: list[tuple[int, str]] = []
    for line in r.text.splitlines():
        parts = line.split()
        if len(parts) != 2:
            continue
        try:
            out.append((int(parts[0]), parts[1]))
        except ValueError:
            continue
    return out


def cross_check_zeros(n: int = 20, dps: int = 25) -> dict:
    """
    Our mpmath zeros vs LMFDB's. Disagreement beyond the expected precision is
    a real finding either way — it means our numerics are wrong, or we are
    reading LMFDB's format wrong. Both are worth knowing before day three.
    """
    from ..lab import zeta as Z
    theirs = lmfdb_zeta_zeros(0.0, n)
    if not theirs:
        return {"ok": None, "reason": "LMFDB nedostupan — nema poređenja",
                "compared": 0}
    ours = Z.zeta_zeros(min(n, len(theirs)), dps)
    diffs = []
    for (idx, s), mine in zip(theirs, ours):
        try:
            diffs.append(abs(float(s) - mine))
        except ValueError:
            continue
    if not diffs:
        return {"ok": None, "reason": "neparsabilan odgovor", "compared": 0}
    worst = max(diffs)
    return {"ok": worst < 1e-9, "compared": len(diffs),
            "max_abs_difference": worst,
            "first_lmfdb": theirs[0][1], "first_ours": repr(ours[0]),
            "reason": ("mpmath i LMFDB se slažu" if worst < 1e-9 else
                       "NESLAGANJE — ne vjeruj numerici dok se ne razriješi")}


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #
SEARCHERS = {
    "arxiv": arxiv_search,
    "openalex": openalex_search,
    "crossref": crossref_search,
    "zbmath": zbmath_search,
    "mathoverflow": stackexchange_search,
}


def search_all(query: str, which: Optional[list] = None,
               per_source: int = 15) -> tuple[list[Item], list[str]]:
    """Run a query across sources. Returns (items, errors) — never raises."""
    items, errors = [], []
    for name in (which or list(SEARCHERS)):
        fn = SEARCHERS.get(name)
        if fn is None:
            continue
        try:
            items.extend(fn(query, per_source))
        except EgressBlocked as e:
            errors.append(f"{name}: {e}")
        except Exception as e:                          # noqa: BLE001
            errors.append(f"{name}: {type(e).__name__}: {e}")
    return items, errors
