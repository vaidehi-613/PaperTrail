from dataclasses import dataclass

from openai import AsyncOpenAI

from backend.config import get_settings
from backend.db import get_supabase
from backend.observability import get_langfuse


@dataclass
class Source:
    id: str
    content: str
    section: str | None
    page: int | None
    is_table: bool
    is_figure: bool
    similarity: float


async def retrieve(query: str, paper_id: str) -> list[Source]:
    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    emb = await client.embeddings.create(input=[query], model=settings.embed_model)
    query_embedding = emb.data[0].embedding

    # Langfuse tracing happens at agent level, skip here to avoid API incompatibility

    sb = await get_supabase()
    result = await sb.rpc(
        "match_chunks_hybrid",
        {
            "query_embedding": query_embedding,
            "query_text": query,
            "filter_paper_id": paper_id,
            "match_count": settings.rerank_candidates,
            "rrf_k": settings.rrf_k,
        },
    ).execute()

    candidates = [Source(**row) for row in result.data]

    # Cross-encoder reranker: run synchronously on CPU (lazy model load on first call).
    from backend.retrieval.reranker import rerank
    return rerank(query, candidates, top_k=settings.retrieval_top_k)
