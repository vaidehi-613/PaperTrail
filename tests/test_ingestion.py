import os
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from backend.ingestion.parser import parse_pdf


# ---------------------------------------------------------------------------
# Unit test — no network calls, no env vars required
# ---------------------------------------------------------------------------

def test_parser_chunks(sample_pdf_path: Path) -> None:
    chunks = parse_pdf(sample_pdf_path)

    assert len(chunks) >= 1, "Parser must return at least one chunk"

    for chunk in chunks:
        assert chunk.content.strip(), "Chunk content must be non-empty"
        assert isinstance(chunk.is_table, bool)
        assert isinstance(chunk.is_figure, bool)
        assert chunk.chunk_index >= 0

    pages = [c.page for c in chunks if c.page is not None]
    assert pages, "At least one chunk must carry a page number"


# ---------------------------------------------------------------------------
# Integration test — requires SUPABASE_URL + OPENAI_API_KEY in environment
# ---------------------------------------------------------------------------

_needs_integration = pytest.mark.skipif(
    not (os.getenv("SUPABASE_URL") and os.getenv("OPENAI_API_KEY")),
    reason="Integration test: set SUPABASE_URL and OPENAI_API_KEY in .env to run",
)


@_needs_integration
@pytest.mark.asyncio
async def test_paper_ingestion_endpoint(sample_pdf_bytes: bytes) -> None:
    from backend.main import app  # deferred — avoids module-level network init

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/papers",
            files={"file": ("sample.pdf", sample_pdf_bytes, "application/pdf")},
        )

    assert response.status_code == 200, response.text
    data = response.json()
    assert "paper_id" in data
    assert data["chunk_count"] >= 1
    paper_id = data["paper_id"]

    from backend.db import get_supabase

    sb = await get_supabase()
    result = await sb.table("chunks").select("*").eq("paper_id", paper_id).execute()
    db_chunks = result.data

    assert len(db_chunks) == data["chunk_count"]
    for row in db_chunks:
        assert row["content"], "content must be non-empty"
        assert row["embedding"] is not None, "embedding must be stored"
        assert isinstance(row["is_table"], bool)
        assert isinstance(row["is_figure"], bool)
        assert row["chunk_index"] is not None

    await sb.table("papers").delete().eq("id", paper_id).execute()
