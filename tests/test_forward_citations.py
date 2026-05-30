"""
Test forward citations tool and UI data flow.
"""
import json
import re
from unittest.mock import AsyncMock, patch

import pytest

from backend.agent.scholar import ScholarResult
from backend.agent.tools import get_forward_citations


def extract_json_from_data_tag(result_str: str) -> dict:
    """Extract JSON from <data type="tool_result">...</data> wrapper."""
    match = re.search(r'<data type="tool_result">(.*?)</data>', result_str, re.DOTALL)
    if not match:
        raise ValueError(f"No <data> tag found in: {result_str}")
    return json.loads(match.group(1))


@pytest.mark.asyncio
async def test_get_forward_citations_success():
    """Forward citations should return citing papers with metadata."""
    mock_resolved = ("https://openalex.org/W2964645440", {
        "title": "Attention Is All You Need",
        "year": 2017,
        "authors": ["Vaswani", "Shazeer"],
        "concepts": ["deep learning", "transformers"],
        "abstract": "The dominant sequence transduction models are based on complex recurrent...",
    })

    mock_citing = [
        ScholarResult(
            title="BERT: Pre-training of Deep Bidirectional Transformers",
            authors=["Devlin", "Chang"],
            year=2018,
            abstract="We introduce BERT...",
            doi="10.18653/v1/N19-1423",
            url="https://aclanthology.org/N19-1423",
            fields_of_study=["NLP"],
        ),
    ]

    with patch("backend.agent.tools.resolve_paper_oa", AsyncMock(return_value=mock_resolved)), \
         patch("backend.agent.tools.get_citing_papers", AsyncMock(return_value=mock_citing)):

        result_str = await get_forward_citations.ainvoke({"paper_title": "Attention Is All You Need"})
        result = extract_json_from_data_tag(result_str)

        assert "resolved_paper" in result
        assert result["resolved_paper"]["title"] == "Attention Is All You Need"
        assert len(result["papers"]) == 1
        assert result["papers"][0]["title"] == "BERT: Pre-training of Deep Bidirectional Transformers"
        assert result["papers"][0]["year"] == 2018
        assert result["papers"][0]["doi"] == "10.18653/v1/N19-1423"


@pytest.mark.asyncio
async def test_get_forward_citations_not_found():
    """Forward citations should handle paper not found gracefully."""
    with patch("backend.agent.tools.resolve_paper_oa", AsyncMock(return_value=None)):
        result_str = await get_forward_citations.ainvoke({"paper_title": "Nonexistent Paper XYZ"})
        result = extract_json_from_data_tag(result_str)

        assert "error" in result
        assert "Could not confidently identify" in result["error"]


@pytest.mark.asyncio
async def test_get_forward_citations_no_citing_papers():
    """Forward citations should handle no citing papers gracefully."""
    mock_resolved = ("https://openalex.org/W123", {
        "title": "Recent Paper",
        "year": 2026,
        "authors": ["Smith"],
        "concepts": [],
    })

    with patch("backend.agent.tools.resolve_paper_oa", AsyncMock(return_value=mock_resolved)), \
         patch("backend.agent.tools.get_citing_papers", AsyncMock(return_value=[])):

        result_str = await get_forward_citations.ainvoke({"paper_title": "Recent Paper"})
        result = extract_json_from_data_tag(result_str)

        assert result["papers"] == []
        assert "note" in result
        assert "No citing papers found" in result["note"]
