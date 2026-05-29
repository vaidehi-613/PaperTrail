import json
import logging

from langchain_core.tools import tool

from backend.agent.scholar import (
    ScholarResult,
    get_citing_papers,
    resolve_paper_oa,
    scholar_keyword_search,
)
from backend.retrieval.retriever import Source, retrieve as _retrieve

logger = logging.getLogger(__name__)


@tool
async def retrieve_paper(query: str, paper_id: str) -> str:
    """Retrieve relevant passages from the uploaded research paper.
    Use for questions about the paper's content, methods, results, or figures."""
    sources: list[Source] = await _retrieve(query, paper_id)
    return json.dumps(
        [
            {
                "id": s.id,
                "content": s.content,
                "section": s.section,
                "page": s.page,
                "is_table": s.is_table,
                "is_figure": s.is_figure,
                "similarity": s.similarity,
            }
            for s in sources
        ]
    )


@tool
async def get_forward_citations(paper_title: str) -> str:
    """Find papers that CITE the given paper (forward citations / 'what came after').
    Pass the full paper title. Uses the Semantic Scholar citations graph — not a keyword search.
    Use for questions like 'what came after this?', 'papers that build on this', 'newer work'."""
    logger.info("[tool] get_forward_citations  paper_title=%r", paper_title)

    resolved = await resolve_paper_oa(paper_title)
    if resolved is None:
        return json.dumps({
            "error": f"Could not confidently identify '{paper_title}' in Semantic Scholar. "
                     "No forward citations retrieved."
        })

    oa_id, meta = resolved
    logger.info(
        "[tool] resolved  oa_id=%s  title=%r  year=%s  authors=%s  concepts=%s",
        oa_id, meta["title"], meta["year"], meta["authors"], meta.get("concepts"),
    )

    citing = await get_citing_papers(oa_id, meta.get("concepts") or [])
    if not citing:
        return json.dumps({
            "resolved_paper": meta,
            "note": "No relevant citing papers found (may be rate-limited or field-filtered).",
            "papers": [],
        })

    return json.dumps({
        "resolved_paper": {
            "title": meta["title"],
            "year": meta["year"],
            "authors": meta["authors"],
            "oa_id": oa_id,
        },
        "papers": [
            {
                "title": r.title,
                "authors": r.authors,
                "year": r.year,
                "abstract": r.abstract,
                "doi": r.doi,
                "url": r.url,
                "fields_of_study": r.fields_of_study,
            }
            for r in citing
        ],
    })


@tool
async def scholar_search_tool(query: str) -> str:
    """Keyword search for related academic papers on Semantic Scholar.
    Use for broad topic discovery — NOT for 'what papers cited this paper' (use get_forward_citations instead)."""
    results: list[ScholarResult] = await scholar_keyword_search(query)
    if not results:
        return json.dumps({
            "note": "No results returned. Semantic Scholar may be rate-limiting — try again in a minute."
        })
    return json.dumps(
        [
            {
                "title": r.title,
                "authors": r.authors,
                "year": r.year,
                "abstract": r.abstract,
                "doi": r.doi,
                "url": r.url,
            }
            for r in results
        ]
    )
