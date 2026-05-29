"""
Scholarly lookup helpers.

forward citations  — OpenAlex (free, no key, 10 req/sec)
keyword search     — Semantic Scholar /paper/search
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

import httpx

from backend.config import get_settings

logger = logging.getLogger(__name__)

_SS_BASE = "https://api.semanticscholar.org/graph/v1"
_SS_SEARCH_FIELDS = "title,year,authors,fieldsOfStudy,externalIds,abstract"

_OA_BASE = "https://api.openalex.org"
# Polite pool: OpenAlex asks for a mailto in the User-Agent
_OA_HEADERS = {"User-Agent": "PaperTrail/1.0 (mailto:papertrail@example.com)"}

# File-based cache so each title is resolved at most once ever (survives restarts).
_CACHE_FILE = Path.home() / ".cache" / "papertrail" / "oa_resolve_cache.json"
_resolve_cache: dict[str, tuple[str, dict]] = {}


def _load_cache() -> None:
    try:
        if _CACHE_FILE.exists():
            data = json.loads(_CACHE_FILE.read_text())
            _resolve_cache.update({k: (v["oa_id"], v["meta"]) for k, v in data.items()})
            logger.info("[scholar] loaded %d cached resolutions from disk", len(_resolve_cache))
    except Exception as exc:
        logger.warning("[scholar] could not load cache: %s", exc)


def _save_cache() -> None:
    try:
        _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {k: {"oa_id": v[0], "meta": v[1]} for k, v in _resolve_cache.items()}
        _CACHE_FILE.write_text(json.dumps(data, indent=2))
    except Exception as exc:
        logger.warning("[scholar] could not save cache: %s", exc)


_load_cache()


@dataclass
class ScholarResult:
    title: str
    authors: list[str]
    year: int | None
    abstract: str | None
    doi: str | None
    url: str | None
    fields_of_study: list[str] | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _title_overlap(a: str, b: str) -> float:
    """Word-level Jaccard similarity (case-insensitive, stopwords removed)."""
    stop = {"a", "an", "the", "of", "in", "and", "for", "is", "on", "with"}
    wa = {w for w in a.lower().split() if w not in stop}
    wb = {w for w in b.lower().split() if w not in stop}
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def _ss_headers() -> dict[str, str]:
    key = get_settings().semantic_scholar_api_key
    return {"x-api-key": key} if key else {}


# ---------------------------------------------------------------------------
# OpenAlex — resolve + forward citations (no rate-limit issues)
# ---------------------------------------------------------------------------

async def resolve_paper_oa(title: str, min_overlap: float = 0.55) -> tuple[str, dict] | None:
    """
    Resolve a paper title to an OpenAlex Work ID.
    Returns (oa_work_id, {title, year, authors, concepts, doi}) or None.
    Results cached on disk permanently.
    """
    if title in _resolve_cache:
        logger.info("[scholar] resolve cache hit for %r", title)
        return _resolve_cache[title]

    url = f"{_OA_BASE}/works"
    params = {
        "filter": f"title.search:{title}",
        "sort": "cited_by_count:desc",  # most-cited = canonical paper
        "per_page": 5,
        "select": "id,title,publication_year,authorships,concepts,doi,is_retracted",
    }
    logger.info("[scholar] resolve_paper_oa  query=%r  url=%s", title, url)

    async with httpx.AsyncClient(timeout=10, headers=_OA_HEADERS) as client:
        resp = await client.get(url, params=params)

    if resp.status_code == 429:
        logger.warning("[scholar] 429 from OpenAlex on resolve — unexpected")
        return None

    resp.raise_for_status()
    items = resp.json().get("results", [])
    logger.info("[scholar] resolve_paper_oa  candidates=%d", len(items))

    for item in items:
        candidate = item.get("title") or ""
        overlap = _title_overlap(title, candidate)
        logger.info("[scholar] candidate  title=%r  year=%s  overlap=%.2f",
                    candidate, item.get("publication_year"), overlap)
        if overlap >= min_overlap:
            oa_id = item["id"]  # e.g. "https://openalex.org/W2963403153"
            concepts = [c["display_name"] for c in (item.get("concepts") or [])
                        if c.get("level", 99) <= 1]
            meta = {
                "title": candidate,
                "year": item.get("publication_year"),
                "authors": [a["author"]["display_name"]
                            for a in (item.get("authorships") or [])[:5]],
                "concepts": concepts,
                "doi": (item.get("doi") or "").replace("https://doi.org/", "") or None,
                "is_retracted": item.get("is_retracted", False),
            }
            logger.info("[scholar] RESOLVED  oa_id=%s  title=%r  year=%s  authors=%s  concepts=%s",
                        oa_id, meta["title"], meta["year"], meta["authors"][:2], meta["concepts"][:3])
            _resolve_cache[title] = (oa_id, meta)
            _save_cache()
            return oa_id, meta

    logger.warning("[scholar] resolve_paper_oa: no confident match for %r", title)
    return None


async def get_citing_papers(
    oa_work_id: str,
    source_concepts: list[str],
    limit: int = 10,
    top_k: int = 5,
) -> list[ScholarResult]:
    """
    Fetch papers that cite oa_work_id via OpenAlex.
    Drops papers whose concepts have zero overlap with source_concepts.
    """
    url = f"{_OA_BASE}/works"
    params = {
        "filter": f"cites:{oa_work_id}",
        "sort": "publication_year:desc",
        "per_page": limit,
        "select": "id,title,publication_year,authorships,concepts,doi,abstract_inverted_index",
    }
    logger.info("[scholar] get_citing_papers  oa_id=%s  url=%s  params=%s",
                oa_work_id, url, params)

    async with httpx.AsyncClient(timeout=15, headers=_OA_HEADERS) as client:
        resp = await client.get(url, params=params)

    if resp.status_code == 429:
        logger.warning("[scholar] 429 from OpenAlex on citations")
        return []

    resp.raise_for_status()
    items = resp.json().get("results", [])
    logger.info("[scholar] citing papers raw count=%d", len(items))

    source_set = {c.lower() for c in source_concepts}
    results: list[ScholarResult] = []

    for item in items:
        if not item.get("title"):
            continue

        paper_concepts = [c["display_name"] for c in (item.get("concepts") or [])
                          if c.get("level", 99) <= 1]
        paper_set = {c.lower() for c in paper_concepts}

        if paper_set and source_set and not paper_set & source_set:
            logger.debug("[scholar] DROPPED  title=%r  concepts=%s", item.get("title"), paper_concepts)
            continue

        doi_full = item.get("doi") or ""
        doi = doi_full.replace("https://doi.org/", "") or None

        # Reconstruct abstract from inverted index (OpenAlex format)
        abstract: str | None = None
        inv = item.get("abstract_inverted_index")
        if inv:
            words = sorted(
                ((pos, word) for word, positions in inv.items() for pos in positions),
                key=lambda x: x[0],
            )
            abstract = " ".join(w for _, w in words)[:500]

        results.append(ScholarResult(
            title=item.get("title", ""),
            authors=[a["author"]["display_name"] for a in (item.get("authorships") or [])[:3]],
            year=item.get("publication_year"),
            abstract=abstract,
            doi=doi,
            url=f"https://doi.org/{doi}" if doi else None,
            fields_of_study=paper_concepts or None,
        ))

    results = results[:top_k]
    logger.info("[scholar] after gate returned=%d", len(results))
    return results


# ---------------------------------------------------------------------------
# Semantic Scholar — keyword search only (kept for general related-work queries)
# ---------------------------------------------------------------------------

async def scholar_keyword_search(query: str, limit: int = 5) -> list[ScholarResult]:
    url = f"{_SS_BASE}/paper/search"
    params = {"query": query, "fields": _SS_SEARCH_FIELDS, "limit": limit}
    logger.info("[scholar] keyword_search  url=%s  params=%s", url, params)

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params, headers=_ss_headers())

    if resp.status_code == 429:
        logger.warning("[scholar] 429 rate-limit on keyword_search")
        return []

    resp.raise_for_status()
    items = resp.json().get("data", [])
    results: list[ScholarResult] = []
    for item in items:
        doi = (item.get("externalIds") or {}).get("DOI")
        results.append(ScholarResult(
            title=item.get("title", ""),
            authors=[a["name"] for a in (item.get("authors") or [])],
            year=item.get("year"),
            abstract=item.get("abstract"),
            doi=doi,
            url=f"https://doi.org/{doi}" if doi else None,
            fields_of_study=item.get("fieldsOfStudy") or None,
        ))
    return results
