import pytest
from httpx import ASGITransport, AsyncClient

from backend.agent.scholar import ScholarResult
from backend.retrieval.retriever import Source

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


@pytest.mark.asyncio
async def test_chat_response_shape(monkeypatch) -> None:
    """POST /chat returns {answer, sources, scholar_results} without hitting real services."""
    from backend.main import app

    async def fake_run_agent(paper_id, question, paper_title=""):
        return FAKE_ANSWER, [FAKE_SOURCE], []

    monkeypatch.setattr("backend.routers.chat.run_agent", fake_run_agent)

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
    assert data["scholar_results"] == []
