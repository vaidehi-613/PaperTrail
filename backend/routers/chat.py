from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, field_validator

from backend.agent.graph import run_agent
from backend.agent.scholar import ScholarResult
from backend.retrieval.retriever import Source
from backend.verifier.checks import VerificationResult

router = APIRouter()


class ChatRequest(BaseModel):
    paper_id: str
    message: str
    paper_title: str = ""

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        if len(v) > 2000:
            raise ValueError("Message too long (max 2000 chars)")
        # Strip control characters except newlines and tabs
        return "".join(c for c in v if c.isprintable() or c in "\n\t")

    @field_validator("paper_title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        if len(v) > 500:
            raise ValueError("Title too long (max 500 chars)")
        return "".join(c for c in v if c.isprintable() or c.isspace())


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


class VerificationResultOut(BaseModel):
    title: str
    status: Literal["verified", "flagged", "not_found", "retracted"]
    doi: str | None
    url: str | None
    note: str | None


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceOut]
    scholar_results: list[ScholarResultOut] = []
    verifications: list[VerificationResultOut] = []


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    answer, paper_sources, scholar_results, verifications = await run_agent(
        req.paper_id, req.message, req.paper_title
    )

    return ChatResponse(
        answer=answer,
        sources=[SourceOut(**vars(s)) for s in paper_sources],
        scholar_results=[ScholarResultOut(**vars(r)) for r in scholar_results],
        verifications=[VerificationResultOut(**vars(v)) for v in verifications],
    )
