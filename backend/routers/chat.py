from openai import AsyncOpenAI
from pydantic import BaseModel
from fastapi import APIRouter

from backend.config import get_settings
from backend.retrieval.retriever import Source, retrieve

router = APIRouter()

_SYSTEM_PROMPT = (
    "You are a research assistant helping a student understand a paper. "
    "Answer only using the provided excerpts. Cite sources inline as "
    "[Section, p.N]. If the answer is not in the excerpts, say so clearly."
)


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


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceOut]


def _fmt_context(sources: list[Source]) -> str:
    parts = []
    for s in sources:
        loc = f"{s.section or 'Section'}, p.{s.page}" if s.page else (s.section or "")
        parts.append(f"[{loc}]\n{s.content}")
    return "\n\n".join(parts)


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    sources = await retrieve(req.message, req.paper_id)

    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    completion = await client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Excerpts:\n{_fmt_context(sources)}\n\nQuestion: {req.message}",
            },
        ],
    )

    answer = completion.choices[0].message.content or ""
    return ChatResponse(
        answer=answer,
        sources=[SourceOut(**vars(s)) for s in sources],
    )
