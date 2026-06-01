import asyncio
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile

from backend.ingestion.embedder import embed_chunks
from backend.ingestion.parser import parse_pdf
from backend.ingestion.store import store_paper

router = APIRouter()


@router.post("")
async def upload_paper(file: UploadFile) -> dict[str, object]:
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    pdf_bytes = await file.read()

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_bytes)
        tmp_path = Path(tmp.name)

    try:
        loop = asyncio.get_event_loop()
        paper_title, chunks = await loop.run_in_executor(None, parse_pdf, tmp_path)

        embeddings = await embed_chunks(chunks)
        paper_id = await store_paper(
            file.filename or "unknown.pdf",
            paper_title,
            chunks,
            embeddings
        )
    finally:
        tmp_path.unlink(missing_ok=True)

    return {
        "paper_id": paper_id,
        "paper_title": paper_title,
        "chunk_count": len(chunks)
    }
