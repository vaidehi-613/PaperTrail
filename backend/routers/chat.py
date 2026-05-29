from fastapi import APIRouter
from pydantic import BaseModel

from backend.agent.graph import run_agent
from backend.agent.scholar import ScholarResult
from backend.retrieval.retriever import Source

router = APIRouter()


class ChatRequest(BaseModel):
    paper_id: str
    message: str


class SourceOut(BaseModel):
    id: str
    content: str
    section: str | None
    page: int | None
    is_table: bool
    is_figure: bool
    similarity: float


class ScholarResultOut(BaseModel):
    title: str
    authors: list[str]
    year: int | None
    abstract: str | None
    doi: str | None
    url: str | None


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceOut]
    scholar_results: list[ScholarResultOut] = []


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    answer, paper_sources, scholar_results = await run_agent(req.paper_id, req.message)

    return ChatResponse(
        answer=answer,
        sources=[SourceOut(**vars(s)) for s in paper_sources],
        scholar_results=[ScholarResultOut(**vars(r)) for r in scholar_results],
    )
