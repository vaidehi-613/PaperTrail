"""
Scholarly lookup helpers.

forward citations  — OpenAlex (free, no key, 10 req/sec)
keyword search     — Semantic Scholar /paper/search
"""
from __future__ import annotations

import json
import logging
import math
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


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two embedding vectors."""
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


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
        "select": "id,title,publication_year,authorships,concepts,doi,is_retracted,abstract_inverted_index",
    }
    logger.info("[scholar] resolve_paper_oa  query=%r  url=%s", title, url)

    async with httpx.AsyncClient(timeout=10, headers=_OA_HEADERS) as client:
        resp = await client.get(url, params=params)

    if resp.status_code == 429:
        logger.warning("[scholar] 429 from OpenAlex on resolve — unexpected")
        return None

    if resp.status_code >= 400:
        logger.warning("[scholar] %d from OpenAlex on resolve  title=%r", resp.status_code, title)
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

            # Reconstruct abstract from inverted index
            abstract: str | None = None
            inv = item.get("abstract_inverted_index")
            if inv:
                words = sorted(
                    ((pos, word) for word, positions in inv.items() for pos in positions),
                    key=lambda x: x[0],
                )
                abstract = " ".join(w for _, w in words)[:500]

            meta = {
                "title": candidate,
                "year": item.get("publication_year"),
                "authors": [a["author"]["display_name"]
                            for a in (item.get("authorships") or [])[:5]],
                "concepts": concepts,
                "doi": (item.get("doi") or "").replace("https://doi.org/", "") or None,
                "is_retracted": item.get("is_retracted", False),
                "abstract": abstract,
            }
            logger.info("[scholar] RESOLVED  oa_id=%s  title=%r  year=%s  authors=%s",
                        oa_id, meta["title"], meta["year"], meta["authors"][:2])
            _resolve_cache[title] = (oa_id, meta)
            _save_cache()
            return oa_id, meta

    logger.warning("[scholar] resolve_paper_oa: no confident match for %r", title)
    return None


async def get_citing_papers(
    oa_work_id: str,
    source_title: str,
    source_abstract: str | None = None,
    top_k: int = 10,
) -> list[ScholarResult]:
    """
    Fetch papers that cite oa_work_id via OpenAlex.
    Ranks by RELEVANCE (embedding similarity to source) + popularity (citation count).
    Paper-agnostic: works for any field, not just NLP.
    """
    from backend.ingestion.embedder import embed_text

    # Fetch large candidate pool (pagination fix)
    url = f"{_OA_BASE}/works"
    params = {
        "filter": f"cites:{oa_work_id}",
        "sort": "cited_by_count:desc",  # pre-sort by citations for initial fetch
        "per_page": 200,  # large pool before relevance ranking
        "select": "id,title,publication_year,authorships,concepts,doi,abstract_inverted_index,cited_by_count",
    }
    logger.info("[scholar] get_citing_papers  oa_id=%s  fetching %d candidates", oa_work_id, params["per_page"])

    async with httpx.AsyncClient(timeout=20, headers=_OA_HEADERS) as client:
        resp = await client.get(url, params=params)

    if resp.status_code == 429:
        logger.warning("[scholar] 429 from OpenAlex on citations")
        return []

    if resp.status_code >= 400:
        logger.warning("[scholar] %d from OpenAlex on citations", resp.status_code)
        return []

    resp.raise_for_status()
    items = resp.json().get("results", [])
    logger.info("[scholar] citing papers raw count=%d", len(items))

    if not items:
        return []

    # Embed source paper (title + abstract for semantic matching)
    source_text = source_title
    if source_abstract:
        source_text = f"{source_title}. {source_abstract[:500]}"
    source_embedding = await embed_text(source_text)

    # Build candidates with embeddings
    candidates: list[tuple[ScholarResult, float, int]] = []  # (result, relevance, citations)

    for item in items:
        if not item.get("title"):
            continue

        paper_concepts = [c["display_name"] for c in (item.get("concepts") or [])
                          if c.get("level", 99) <= 1]

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

        # Compute relevance via embedding similarity
        candidate_text = item.get("title", "")
        if abstract:
            candidate_text = f"{candidate_text}. {abstract[:300]}"

        try:
            candidate_embedding = await embed_text(candidate_text)
            relevance = _cosine_similarity(source_embedding, candidate_embedding)
        except Exception as exc:
            logger.warning("[scholar] embedding failed for %r: %s", item.get("title"), exc)
            relevance = 0.0

        citation_count = item.get("cited_by_count", 0)

        result = ScholarResult(
            title=item.get("title", ""),
            authors=[a["author"]["display_name"] for a in (item.get("authorships") or [])[:3]],
            year=item.get("publication_year"),
            abstract=abstract,
            doi=doi,
            url=f"https://doi.org/{doi}" if doi else None,
            fields_of_study=paper_concepts or None,
        )

        candidates.append((result, relevance, citation_count))

    # Normalize citation counts to [0, 1]
    max_citations = max((c for _, _, c in candidates), default=1)
    normalized_candidates = [
        (result, relevance, cites / max_citations if max_citations > 0 else 0)
        for result, relevance, cites in candidates
    ]

    # Blend: 60% relevance + 40% popularity
    RELEVANCE_WEIGHT = 0.6
    POPULARITY_WEIGHT = 0.4

    scored = [
        (result, RELEVANCE_WEIGHT * rel + POPULARITY_WEIGHT * norm_cites, rel, cites)
        for result, rel, norm_cites in normalized_candidates
        for cites in [next(c for r, _, c in candidates if r == result)]  # recover raw citation count
    ]

    # Sort by blended score, descending
    scored.sort(key=lambda x: x[1], reverse=True)

    # Log top candidates for debugging
    logger.info("[scholar] TOP CANDIDATES (relevance-ranked):")
    for i, (result, blended_score, relevance, citations) in enumerate(scored[:15], 1):
        logger.info(
            "[scholar]   %2d. score=%.3f (rel=%.3f, cites=%d)  %s",
            i, blended_score, relevance, citations, result.title[:80]
        )

    return [r for r, _, _, _ in scored[:top_k]]


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
