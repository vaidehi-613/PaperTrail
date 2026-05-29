"""
Semantic Scholar helpers.

Two distinct operations:
  scholar_keyword_search  — /paper/search (general related-work queries)
  get_forward_citations   — resolve paper by title → /paper/{id}/citations
                            with a fieldsOfStudy relevance gate
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from backend.config import get_settings

logger = logging.getLogger(__name__)

_BASE = "https://api.semanticscholar.org/graph/v1"
_SEARCH_FIELDS = "title,year,authors,fieldsOfStudy,externalIds"
_CITE_FIELDS = (
    "citingPaper.title,citingPaper.year,citingPaper.authors,"
    "citingPaper.abstract,citingPaper.externalIds,citingPaper.fieldsOfStudy"
)


@dataclass
class ScholarResult:
    title: str
    authors: list[str]
    year: int | None
    abstract: str | None
    doi: str | None
    url: str | None
    fields_of_study: list[str] | None = None


def _headers() -> dict[str, str]:
    key = get_settings().semantic_scholar_api_key
    return {"x-api-key": key} if key else {}


def _handle_rate_limit(resp: httpx.Response, context: str) -> bool:
    """Return True if rate-limited (caller should return empty)."""
    if resp.status_code == 429:
        logger.warning("[scholar] 429 rate-limit on %s", context)
        return True
    return False


# ---------------------------------------------------------------------------
# Step 1 — resolve a paper's Semantic Scholar ID by title
# ---------------------------------------------------------------------------

def _title_overlap(a: str, b: str) -> float:
    """Word-level Jaccard similarity between two titles (case-insensitive)."""
    stop = {"a", "an", "the", "of", "in", "and", "for", "is", "on"}
    wa = {w for w in a.lower().split() if w not in stop}
    wb = {w for w in b.lower().split() if w not in stop}
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


async def resolve_paper_ss(
    title: str,
    min_overlap: float = 0.6,
) -> tuple[str, dict] | None:
    """
    Resolve a paper to its Semantic Scholar paper ID.
    Returns (ss_paper_id, {title, year, authors, fields_of_study}) or None.
    Logs the resolved title/year/authors so callers can confirm the match.
    """
    url = f"{_BASE}/paper/search"
    params = {"query": title, "fields": _SEARCH_FIELDS, "limit": 5}
    logger.info("[scholar] resolve_paper_ss  query=%r  url=%s  params=%s", title, url, params)

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params, headers=_headers())

    if _handle_rate_limit(resp, "resolve"):
        return None

    resp.raise_for_status()
    items = resp.json().get("data", [])
    logger.info("[scholar] resolve_paper_ss  candidates=%d", len(items))

    for item in items:
        candidate_title = item.get("title", "")
        overlap = _title_overlap(title, candidate_title)
        logger.info(
            "[scholar] candidate  title=%r  year=%s  overlap=%.2f",
            candidate_title, item.get("year"), overlap,
        )
        if overlap >= min_overlap:
            ss_id = item["paperId"]
            meta = {
                "title": candidate_title,
                "year": item.get("year"),
                "authors": [a["name"] for a in (item.get("authors") or [])],
                "fields_of_study": item.get("fieldsOfStudy") or [],
            }
            logger.info(
                "[scholar] RESOLVED  ss_id=%s  title=%r  year=%s  authors=%s  fields=%s",
                ss_id, meta["title"], meta["year"], meta["authors"], meta["fields_of_study"],
            )
            return ss_id, meta

    logger.warning("[scholar] resolve_paper_ss: no confident match for %r", title)
    return None


# ---------------------------------------------------------------------------
# Step 2 — forward citations with relevance gate
# ---------------------------------------------------------------------------

async def get_citing_papers(
    ss_paper_id: str,
    source_fields: list[str],
    limit: int = 20,
    top_k: int = 5,
) -> list[ScholarResult]:
    """
    Fetch papers that CITE ss_paper_id via /paper/{id}/citations.
    Drops results whose fieldsOfStudy has zero overlap with source_fields.
    """
    url = f"{_BASE}/paper/{ss_paper_id}/citations"
    params = {"fields": _CITE_FIELDS, "limit": limit}
    logger.info(
        "[scholar] get_citing_papers  ss_paper_id=%s  url=%s  params=%s",
        ss_paper_id, url, params,
    )

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url, params=params, headers=_headers())

    if _handle_rate_limit(resp, "citations"):
        return []

    resp.raise_for_status()

    raw = resp.json().get("data", [])
    logger.info("[scholar] citations raw count=%d", len(raw))

    source_field_set = {f.lower() for f in source_fields}
    results: list[ScholarResult] = []

    for entry in raw:
        paper = entry.get("citingPaper", {})
        if not paper.get("title"):
            continue

        paper_fields = [f for f in (paper.get("fieldsOfStudy") or [])]
        paper_field_set = {f.lower() for f in paper_fields}

        # Relevance gate: if the paper has fields declared, they must overlap.
        if paper_field_set and not paper_field_set & source_field_set:
            logger.debug(
                "[scholar] DROPPED (field mismatch)  title=%r  fields=%s",
                paper.get("title"), paper_fields,
            )
            continue

        doi = (paper.get("externalIds") or {}).get("DOI")
        results.append(
            ScholarResult(
                title=paper.get("title", ""),
                authors=[a["name"] for a in (paper.get("authors") or [])],
                year=paper.get("year"),
                abstract=paper.get("abstract"),
                doi=doi,
                url=f"https://doi.org/{doi}" if doi else None,
                fields_of_study=paper_fields or None,
            )
        )

    # Sort newest first, cap at top_k
    results.sort(key=lambda r: r.year or 0, reverse=True)
    results = results[:top_k]
    logger.info("[scholar] after gate top_k=%d  returned=%d", top_k, len(results))
    return results


# ---------------------------------------------------------------------------
# Step 3 — keyword search (unchanged, for general related-work queries)
# ---------------------------------------------------------------------------

async def scholar_keyword_search(query: str, limit: int = 5) -> list[ScholarResult]:
    url = f"{_BASE}/paper/search"
    params = {"query": query, "fields": _SEARCH_FIELDS + ",abstract", "limit": limit}
    logger.info("[scholar] keyword_search  url=%s  params=%s", url, params)

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params, headers=_headers())

    if _handle_rate_limit(resp, "keyword_search"):
        return []

    resp.raise_for_status()
    items = resp.json().get("data", [])
    results: list[ScholarResult] = []
    for item in items:
        doi = (item.get("externalIds") or {}).get("DOI")
        results.append(
            ScholarResult(
                title=item.get("title", ""),
                authors=[a["name"] for a in (item.get("authors") or [])],
                year=item.get("year"),
                abstract=item.get("abstract"),
                doi=doi,
                url=f"https://doi.org/{doi}" if doi else None,
                fields_of_study=item.get("fieldsOfStudy") or None,
            )
        )
    return results
