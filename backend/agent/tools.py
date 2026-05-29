import json

from langchain_core.tools import tool

from backend.agent.scholar import ScholarResult, scholar_search as _scholar_search
from backend.retrieval.retriever import Source, retrieve as _retrieve


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
async def scholar_search_tool(query: str) -> str:
    """Search Semantic Scholar for related academic papers.
    Use for questions about what came after this paper, related work, or newer studies."""
    results: list[ScholarResult] = await _scholar_search(query)
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
