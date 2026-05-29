from __future__ import annotations

import json
from typing import Annotated

from langchain_core.messages import BaseMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

from backend.agent.scholar import ScholarResult
from backend.agent.tools import retrieve_paper, scholar_search_tool
from backend.config import get_settings
from backend.retrieval.retriever import Source

_TOOLS = [retrieve_paper, scholar_search_tool]
_TOOL_NODE = ToolNode(_TOOLS)

_SYSTEM_TEMPLATE = (
    "You are a research assistant helping a student understand a paper.\n"
    "The uploaded paper ID is: {paper_id}\n\n"
    "Available tools:\n"
    "- retrieve_paper: fetch relevant passages from the paper. Always pass paper_id='{paper_id}'.\n"
    "- scholar_search_tool: find related / newer academic papers on Semantic Scholar.\n\n"
    "Rules:\n"
    "• For questions about the paper's content → call retrieve_paper.\n"
    "• For questions about related/newer work → call scholar_search_tool.\n"
    "• You may call both if the question warrants it.\n"
    "• After gathering context, write a concise answer citing sources as [Section, p.N].\n"
    "• If the excerpts don't contain the answer, say so clearly."
)


class AgentState(TypedDict):
    paper_id: str
    messages: Annotated[list[BaseMessage], add_messages]


def _router_node(state: AgentState) -> dict:
    settings = get_settings()
    llm = ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.openai_api_key,
    ).bind_tools(_TOOLS)
    response = llm.invoke(state["messages"])
    return {"messages": [response]}


def _should_continue(state: AgentState) -> str:
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "continue"
    return "end"


def _build() -> object:
    g = StateGraph(AgentState)
    g.add_node("router", _router_node)
    g.add_node("tools", _TOOL_NODE)
    g.set_entry_point("router")
    g.add_conditional_edges("router", _should_continue, {"continue": "tools", "end": END})
    g.add_edge("tools", "router")
    return g.compile()


_graph = _build()


def _parse_tool_messages(
    messages: list[BaseMessage],
) -> tuple[list[Source], list[ScholarResult]]:
    paper_sources: list[Source] = []
    scholar_results: list[ScholarResult] = []

    for msg in messages:
        if not isinstance(msg, ToolMessage):
            continue
        try:
            data = json.loads(msg.content)
        except (json.JSONDecodeError, TypeError):
            continue

        if msg.name == "retrieve_paper":
            for row in data:
                paper_sources.append(Source(**row))
        elif msg.name == "scholar_search_tool":
            for row in data:
                scholar_results.append(ScholarResult(**row))

    return paper_sources, scholar_results


async def run_agent(
    paper_id: str, question: str
) -> tuple[str, list[Source], list[ScholarResult]]:
    system_msg = SystemMessage(
        content=_SYSTEM_TEMPLATE.format(paper_id=paper_id)
    )
    from langchain_core.messages import HumanMessage
    human_msg = HumanMessage(content=question)

    result = await _graph.ainvoke(
        {"paper_id": paper_id, "messages": [system_msg, human_msg]}
    )

    answer = result["messages"][-1].content or ""
    paper_sources, scholar_results = _parse_tool_messages(result["messages"])
    return answer, paper_sources, scholar_results
