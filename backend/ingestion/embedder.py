from openai import AsyncOpenAI

from backend.config import get_settings
from backend.ingestion.parser import Chunk


async def embed_chunks(chunks: list[Chunk]) -> list[list[float]]:
    if not chunks:
        return []

    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    response = await client.embeddings.create(
        input=[c.content for c in chunks],
        model=settings.embed_model,
    )
    return [item.embedding for item in response.data]


async def embed_text(text: str) -> list[float]:
    """Embed a single text string (for relevance scoring)."""
    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    response = await client.embeddings.create(
        input=[text],
        model=settings.embed_model,
    )
    return response.data[0].embedding
