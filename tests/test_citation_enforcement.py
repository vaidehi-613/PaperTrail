"""
Test that inline citations are enforced in LLM answers.
"""
import re

import pytest

from backend.agent.graph import _validate_citations_present
from backend.retrieval.retriever import Source


def test_validate_citations_present():
    """Citations should be detected in answers with proper format."""
    sources = [
        Source(
            id="1",
            content="The transformer architecture...",
            section="Introduction",
            page=1,
            is_table=False,
            is_figure=False,
            similarity=0.9,
        )
    ]

    # Valid: has citation
    answer_with_citation = "The transformer uses self-attention [Introduction, p.1]."
    assert _validate_citations_present(answer_with_citation, sources) is True

    # Valid: table citation
    answer_with_table = "Results are shown in [Table 1, p.5]."
    assert _validate_citations_present(answer_with_table, sources) is True

    # Valid: figure citation
    answer_with_figure = "Figure 2 illustrates the architecture [Figure 2, p.3]."
    assert _validate_citations_present(answer_with_figure, sources) is True

    # Valid: page-only citation
    answer_page_only = "The model achieves 95% accuracy [p.7]."
    assert _validate_citations_present(answer_page_only, sources) is True

    # Invalid: no citation
    answer_no_citation = "The transformer uses self-attention mechanisms."
    assert _validate_citations_present(answer_no_citation, sources) is False


def test_citation_format_regex():
    """Test the citation pattern matches expected formats."""
    pattern = r'\[[^\]]*p\.\d+\]'

    # Should match
    assert re.search(pattern, "[Section 3.2, p.5]")
    assert re.search(pattern, "[Table 1, p.7]")
    assert re.search(pattern, "[Figure 2, p.3]")
    assert re.search(pattern, "[p.10]")
    assert re.search(pattern, "[Introduction, p.1]")
    assert re.search(pattern, "[Methods, p.3]")

    # Should NOT match (missing page or no brackets)
    assert not re.search(pattern, "[Section 3]")
    assert not re.search(pattern, "[Table 1]")
    assert not re.search(pattern, "Section 3, p.5")  # No brackets


def test_no_sources_no_validation():
    """If no sources retrieved, validation should pass (e.g., 'not covered' answers)."""
    answer = "This paper doesn't cover that topic."
    assert _validate_citations_present(answer, []) is True
