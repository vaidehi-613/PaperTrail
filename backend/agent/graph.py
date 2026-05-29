from __future__ import annotations

import json
import logging
from typing import Annotated

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

from backend.agent.scholar import ScholarResult
from backend.agent.tools import get_forward_citations, retrieve_paper, scholar_search_tool
from backend.config import get_settings
from backend.retrieval.retriever import Source
from backend.verifier.checks import VerificationResult, verify_scholar_results

logger = logging.getLogger(__name__)

_TOOLS = [retrieve_paper, get_forward_citations, scholar_search_tool]
_TOOL_NODE = ToolNode(_TOOLS)

_SYSTEM_TEMPLATE = (
    "You are a research assistant helping a student understand a research paper.\n"
    "Paper title / filename: {paper_title}\n"
    "Internal paper ID (do NOT mention this in answers): {paper_id}\n\n"
    "Available tools:\n"
    "- retrieve_paper: fetch relevant passages from the paper. Always pass paper_id='{paper_id}'.\n"
    "- get_forward_citations: find papers that CITE this paper (forward citation graph).\n"
    "  Pass the FULL paper title (e.g. 'Attention Is All You Need').\n"
    "  Use for: 'what came after', 'newer papers', 'papers that build on this'.\n"
    "- scholar_search_tool: broad keyword search on Semantic Scholar.\n"
    "  Use for: general related-work discovery, NOT for forward citations.\n\n"
    "Rules:\n"
    "• Questions about content → retrieve_paper.\n"
    "• 'What came after / newer / citing papers' → get_forward_citations with the full paper title.\n"
    "• General related-work → scholar_search_tool.\n"
    "• You may call multiple tools if the question warrants it.\n"
    "• Cite paper passages as [Section, p.N].\n"
    "• NEVER reveal the paper_id UUID."
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
            if isinstance(data, list):
                for row in data:
                    paper_sources.append(Source(**row))

        elif msg.name == "get_forward_citations":
            if isinstance(data, dict) and "papers" in data:
                for row in data["papers"]:
                    scholar_results.append(ScholarResult(
                        title=row["title"],
                        authors=row["authors"],
                        year=row["year"],
                        abstract=row["abstract"],
                        doi=row["doi"],
                        url=row["url"],
                        fields_of_study=row.get("fields_of_study"),
                    ))

        elif msg.name == "scholar_search_tool":
            if isinstance(data, list):
                for row in data:
                    scholar_results.append(ScholarResult(
                        title=row["title"],
                        authors=row["authors"],
                        year=row["year"],
                        abstract=row["abstract"],
                        doi=row["doi"],
                        url=row["url"],
                    ))

    return paper_sources, scholar_results


async def run_agent(
    paper_id: str, question: str, paper_title: str = ""
) -> tuple[str, list[Source], list[ScholarResult], list[VerificationResult]]:
    system_msg = SystemMessage(
        content=_SYSTEM_TEMPLATE.format(
            paper_id=paper_id,
            paper_title=paper_title or "unknown",
        )
    )
    human_msg = HumanMessage(content=question)

    logger.info(
        "[agent] run_agent  paper_id=%s  paper_title=%r  question=%r",
        paper_id, paper_title, question,
    )

    result = await _graph.ainvoke(
        {"paper_id": paper_id, "messages": [system_msg, human_msg]}
    )

    answer = result["messages"][-1].content or ""
    paper_sources, scholar_results = _parse_tool_messages(result["messages"])

    # Run verifier on scholar results
    verifications: list[VerificationResult] = []
    if scholar_results:
        verifications = await verify_scholar_results(answer, scholar_results)

        # Reflection loop: regenerate if any citation is not_found or retracted
        bad = [v.title for v in verifications if v.status in ("not_found", "retracted")]
        if bad:
            logger.info("[agent] reflection loop  bad_citations=%s", bad)
            rejection_note = (
                "\n\nIMPORTANT: The following citations could not be verified or are retracted "
                f"— do NOT cite them: {', '.join(bad)}"
            )
            system_msg_retry = SystemMessage(
                content=_SYSTEM_TEMPLATE.format(
                    paper_id=paper_id,
                    paper_title=paper_title or "unknown",
                ) + rejection_note
            )
            result2 = await _graph.ainvoke(
                {"paper_id": paper_id, "messages": [system_msg_retry, human_msg]}
            )
            answer = result2["messages"][-1].content or ""
            paper_sources, scholar_results = _parse_tool_messages(result2["messages"])
            if scholar_results:
                verifications = await verify_scholar_results(answer, scholar_results)

    return answer, paper_sources, scholar_results, verifications
