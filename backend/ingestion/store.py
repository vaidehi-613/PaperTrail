from backend.db import get_supabase
from backend.ingestion.parser import Chunk


async def store_paper(
    filename: str,
    paper_title: str,
    chunks: list[Chunk],
    embeddings: list[list[float]],
) -> str:
    sb = await get_supabase()

    # Try to insert with title, fall back to filename-only if column doesn't exist
    try:
        paper_resp = await sb.table("papers").insert({
            "filename": filename,
            "title": paper_title,
        }).execute()
    except Exception:
        # Fallback: title column doesn't exist yet
        paper_resp = await sb.table("papers").insert({
            "filename": filename,
        }).execute()
    paper_id: str = paper_resp.data[0]["id"]

    rows = [
        {
            "paper_id": paper_id,
            "content": chunk.content,
            "embedding": embedding,
            "section": chunk.section,
            "page": chunk.page,
            "is_table": chunk.is_table,
            "is_figure": chunk.is_figure,
            "chunk_index": chunk.chunk_index,
        }
        for chunk, embedding in zip(chunks, embeddings)
    ]

    await sb.table("chunks").insert(rows).execute()
    return paper_id
