import pytest
from httpx import ASGITransport, AsyncClient

from backend.retrieval.retriever import Source

# ---------------------------------------------------------------------------
# Helpers — fake OpenAI completion
# ---------------------------------------------------------------------------

FAKE_ANSWER = "RAG improves factuality according to [Methods, p.2]."
FAKE_SOURCE = Source(
    id="chunk-1",
    content="RAG improves factuality.",
    section="Methods",
    page=2,
    is_table=False,
    is_figure=False,
    similarity=0.92,
)


class _FakeMessage:
    content = FAKE_ANSWER


class _FakeChoice:
    message = _FakeMessage()


class _FakeCompletion:
    choices = [_FakeChoice()]


class _FakeCompletions:
    async def create(self, **_kwargs):
        return _FakeCompletion()


class _FakeChat:
    completions = _FakeCompletions()


class _FakeOpenAI:
    chat = _FakeChat()

    def __init__(self, **_kwargs):
        pass


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chat_response_shape(monkeypatch) -> None:
    """POST /chat returns {answer, sources} without hitting real services."""
    from backend.main import app

    async def fake_retrieve(query, paper_id, top_k=5):
        return [FAKE_SOURCE]

    from backend.main import app  # deferred — avoids module-level network init

    monkeypatch.setattr("backend.routers.chat.retrieve", fake_retrieve)
    monkeypatch.setattr("backend.routers.chat.AsyncOpenAI", _FakeOpenAI)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/chat",
            json={"paper_id": "paper-123", "message": "What is RAG?"},
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["answer"] == FAKE_ANSWER
    assert len(data["sources"]) == 1
    src = data["sources"][0]
    assert src["content"] == "RAG improves factuality."
    assert src["section"] == "Methods"
    assert src["page"] == 2
    assert src["is_table"] is False
    assert src["is_figure"] is False
