import json
import logging

from langchain_core.tools import tool

from backend.agent.scholar import (
    ScholarResult,
    get_citing_papers,
    resolve_paper_oa,
    scholar_keyword_search,
)
from backend.guardrails import wrap_data
from backend.retrieval.retriever import Source, retrieve as _retrieve

logger = logging.getLogger(__name__)


@tool
async def retrieve_paper(query: str, paper_id: str) -> str:
    """Retrieve relevant passages from the uploaded research paper.
    Use for questions about the paper's content, methods, results, or figures."""
    sources: list[Source] = await _retrieve(query, paper_id)

    # Prepare chunks for LLM (with citation hints in content)
    chunks_for_llm = []
    # Prepare clean chunks for frontend (no citation hints)
    chunks_clean = []

    for s in sources:
        # Build citation hint for the LLM
        citation_hint = ""
        if s.is_table:
            citation_hint = f"[This is Table from {s.section or 'unknown section'}, p.{s.page}]"
        elif s.is_figure:
            citation_hint = f"[This is Figure from {s.section or 'unknown section'}, p.{s.page}]"
        else:
            citation_hint = f"[From {s.section or 'unknown section'}, p.{s.page}]"

        chunks_for_llm.append({
            "content": f"{citation_hint}\n{s.content}",
            "section": s.section,
            "page": s.page,
            "is_table": s.is_table,
            "is_figure": s.is_figure,
        })

        chunks_clean.append({
            "id": s.id,
            "content": s.content,
            "section": s.section,
            "page": s.page,
            "is_table": s.is_table,
            "is_figure": s.is_figure,
            "similarity": s.similarity,
        })

    instruction = (
        "Retrieved chunks from the paper. IMPORTANT: When answering, you MUST include inline citations "
        "using the format [Section Name, p.X] or [Table N, p.X] or [Figure N, p.X]. "
        "Each chunk starts with a citation hint. NEVER answer without citing the source.\n\n"
        f"Chunks for LLM context:\n{json.dumps(chunks_for_llm)}"
    )

    # Return clean chunks (parseable by frontend)
    result = json.dumps(chunks_clean)
    return wrap_data(f"{instruction}\n\n{result}", "tool_result")


@tool
async def get_forward_citations(paper_title: str) -> str:
    """Find papers that CITE the given paper (forward citations / 'what came after').
    Pass the full paper title. Uses OpenAlex citations graph with relevance-based ranking.
    Use for questions like 'what came after this?', 'papers that build on this', 'newer work'."""
    logger.info("[tool] get_forward_citations  paper_title=%r", paper_title)

    resolved = await resolve_paper_oa(paper_title)
    if resolved is None:
        result = json.dumps({
            "error": f"Could not confidently identify '{paper_title}' in OpenAlex. "
                     "No forward citations retrieved."
        })
        return wrap_data(result, "tool_result")

    oa_id, meta = resolved
    logger.info(
        "[tool] resolved  oa_id=%s  title=%r  year=%s  authors=%s",
        oa_id, meta["title"], meta["year"], meta["authors"][:2],
    )

    # Pass source title + abstract for relevance-based ranking
    source_abstract = meta.get("abstract")  # OpenAlex may not have abstract in resolve
    citing = await get_citing_papers(
        oa_id,
        source_title=meta["title"],
        source_abstract=source_abstract,
        top_k=10,
    )

    if not citing:
        result = json.dumps({
            "resolved_paper": meta,
            "note": "No citing papers found (may be rate-limited or no citations yet).",
            "papers": [],
        })
        return wrap_data(result, "tool_result")

    result = json.dumps({
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
    return wrap_data(result, "tool_result")


@tool
async def scholar_search_tool(query: str) -> str:
    """Keyword search for related academic papers on Semantic Scholar.
    Use for broad topic discovery — NOT for 'what papers cited this paper' (use get_forward_citations instead)."""
    results: list[ScholarResult] = await scholar_keyword_search(query)
    if not results:
        result = json.dumps({
            "note": "No results returned. Semantic Scholar may be rate-limiting — try again in a minute."
        })
        return wrap_data(result, "tool_result")
    result = json.dumps(
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
    return wrap_data(result, "tool_result")
