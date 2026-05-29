import json

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from backend.agent.graph import _parse_tool_messages, run_agent
from backend.agent.scholar import ScholarResult
from backend.retrieval.retriever import Source

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FAKE_SOURCE = {
    "id": "chunk-1",
    "content": "Self-attention relates positions in parallel.",
    "section": "3.2 Attention",
    "page": 4,
    "is_table": False,
    "is_figure": False,
    "similarity": 0.93,
}

FAKE_SCHOLAR = {
    "title": "BERT: Pre-training of Deep Bidirectional Transformers",
    "authors": ["Jacob Devlin", "Ming-Wei Chang"],
    "year": 2019,
    "abstract": "We introduce BERT...",
    "doi": "10.18653/v1/N19-1423",
    "url": "https://doi.org/10.18653/v1/N19-1423",
}


# ---------------------------------------------------------------------------
# Unit: _parse_tool_messages
# ---------------------------------------------------------------------------

def test_parse_tool_messages_retrieve() -> None:
    msgs = [
        SystemMessage(content="sys"),
        HumanMessage(content="question"),
        AIMessage(content="", tool_calls=[{"name": "retrieve_paper", "id": "t1", "args": {}}]),
        ToolMessage(content=json.dumps([FAKE_SOURCE]), name="retrieve_paper", tool_call_id="t1"),
        AIMessage(content="The answer."),
    ]
    sources, scholar = _parse_tool_messages(msgs)
    assert len(sources) == 1
    assert sources[0].section == "3.2 Attention"
    assert len(scholar) == 0


def test_parse_tool_messages_scholar() -> None:
    msgs = [
        SystemMessage(content="sys"),
        HumanMessage(content="question"),
        AIMessage(content="", tool_calls=[{"name": "scholar_search_tool", "id": "t2", "args": {}}]),
        ToolMessage(content=json.dumps([FAKE_SCHOLAR]), name="scholar_search_tool", tool_call_id="t2"),
        AIMessage(content="Related work found."),
    ]
    sources, scholar = _parse_tool_messages(msgs)
    assert len(sources) == 0
    assert len(scholar) == 1
    assert scholar[0].title.startswith("BERT")


# ---------------------------------------------------------------------------
# Integration: run_agent (graph mocked)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_agent_retrieve_path(monkeypatch) -> None:
    """Agent routes to retrieve_paper and returns sources."""

    class _FakeGraph:
        async def ainvoke(self, state, **_kwargs):
            tool_msg = ToolMessage(
                content=json.dumps([FAKE_SOURCE]),
                name="retrieve_paper",
                tool_call_id="t1",
            )
            answer_msg = AIMessage(
                content="Self-attention parallelises position processing [3.2 Attention, p.4]."
            )
            return {"messages": state["messages"] + [tool_msg, answer_msg]}

    monkeypatch.setattr("backend.agent.graph._graph", _FakeGraph())

    answer, sources, scholar = await run_agent("paper-123", "How does self-attention work?")

    assert "self-attention" in answer.lower()
    assert len(sources) == 1
    assert sources[0].section == "3.2 Attention"
    assert len(scholar) == 0


@pytest.mark.asyncio
async def test_run_agent_scholar_path(monkeypatch) -> None:
    """Agent routes to scholar_search_tool and returns scholar results."""

    class _FakeGraph:
        async def ainvoke(self, state, **_kwargs):
            tool_msg = ToolMessage(
                content=json.dumps([FAKE_SCHOLAR]),
                name="scholar_search_tool",
                tool_call_id="t2",
            )
            answer_msg = AIMessage(content="Papers that built on this include BERT (2019).")
            return {"messages": state["messages"] + [tool_msg, answer_msg]}

    monkeypatch.setattr("backend.agent.graph._graph", _FakeGraph())

    answer, sources, scholar = await run_agent("paper-123", "What came after this paper?")

    assert "BERT" in answer
    assert len(sources) == 0
    assert len(scholar) == 1
    assert scholar[0].year == 2019
