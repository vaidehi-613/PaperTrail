from dataclasses import dataclass

from openai import AsyncOpenAI

from backend.config import get_settings
from backend.db import get_supabase


@dataclass
class Source:
    id: str
    content: str
    section: str | None
    page: int | None
    is_table: bool
    is_figure: bool
    similarity: float


async def retrieve(query: str, paper_id: str, top_k: int = 5) -> list[Source]:
    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    emb = await client.embeddings.create(input=[query], model=settings.embed_model)
    query_embedding = emb.data[0].embedding

    sb = await get_supabase()
    result = await sb.rpc(
        "match_chunks",
        {
            "query_embedding": query_embedding,
            "filter_paper_id": paper_id,
            "match_count": top_k,
        },
    ).execute()

    return [Source(**row) for row in result.data]
