from dataclasses import dataclass, field

import httpx

from backend.config import get_settings

_BASE = "https://api.semanticscholar.org/graph/v1"
_FIELDS = "title,authors,year,abstract,externalIds"


@dataclass
class ScholarResult:
    title: str
    authors: list[str]
    year: int | None
    abstract: str | None
    doi: str | None
    url: str | None


async def scholar_search(query: str, limit: int = 5) -> list[ScholarResult]:
    settings = get_settings()
    headers = {}
    if settings.semantic_scholar_api_key:
        headers["x-api-key"] = settings.semantic_scholar_api_key

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{_BASE}/paper/search",
            params={"query": query, "fields": _FIELDS, "limit": limit},
            headers=headers,
        )
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
            )
        )
    return results
