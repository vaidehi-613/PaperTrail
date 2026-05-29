"""
Tests for the Semantic Scholar helpers.

Integration tests (marked with @pytest.mark.integration) hit the real
Semantic Scholar API — they run only when --integration is passed or
SEMANTIC_SCHOLAR_INTEGRATION=1 is set in the environment.

Unit tests run with no network access.
"""
from __future__ import annotations

import os
import pytest

_INTEGRATION = os.getenv("SEMANTIC_SCHOLAR_INTEGRATION", "") == "1"
integration = pytest.mark.skipif(
    not _INTEGRATION,
    reason="Set SEMANTIC_SCHOLAR_INTEGRATION=1 to run live Semantic Scholar tests",
)


# ---------------------------------------------------------------------------
# Unit — title overlap (no network)
# ---------------------------------------------------------------------------

def test_title_overlap_exact():
    from backend.agent.scholar import _title_overlap
    assert _title_overlap("Attention Is All You Need", "Attention Is All You Need") == 1.0


def test_title_overlap_partial():
    from backend.agent.scholar import _title_overlap
    score = _title_overlap("Attention Is All You Need", "BERT Pre-training Transformers")
    assert 0.0 <= score < 0.5  # low overlap — different papers


def test_title_overlap_high():
    from backend.agent.scholar import _title_overlap
    score = _title_overlap(
        "Attention Is All You Need",
        "Attention is all you need for vision",
    )
    assert score >= 0.5  # shares most words


# ---------------------------------------------------------------------------
# Unit — relevance gate (no network, uses real filter logic)
# ---------------------------------------------------------------------------

def test_relevance_gate_drops_unrelated():
    """Medicine/Biology papers should be dropped when source is Computer Science."""
    from backend.agent.scholar import ScholarResult, _title_overlap

    source_fields = ["Computer Science"]
    source_set = {f.lower() for f in source_fields}

    unrelated = ScholarResult(
        title="Gingival Overgrowth Drug Study",
        authors=["A. Dentist"],
        year=2025,
        abstract=None,
        doi=None,
        url=None,
        fields_of_study=["Medicine", "Biology"],
    )

    paper_field_set = {f.lower() for f in (unrelated.fields_of_study or [])}
    overlaps = bool(paper_field_set & source_set)
    assert not overlaps, "Medicine paper should NOT overlap with Computer Science"


def test_relevance_gate_keeps_cs_paper():
    from backend.agent.scholar import ScholarResult

    source_fields = ["Computer Science"]
    source_set = {f.lower() for f in source_fields}

    cs_paper = ScholarResult(
        title="BERT: Pre-training of Deep Bidirectional Transformers",
        authors=["Jacob Devlin"],
        year=2019,
        abstract=None,
        doi=None,
        url=None,
        fields_of_study=["Computer Science"],
    )

    paper_field_set = {f.lower() for f in (cs_paper.fields_of_study or [])}
    overlaps = bool(paper_field_set & source_set)
    assert overlaps, "CS paper SHOULD overlap with Computer Science source"


# ---------------------------------------------------------------------------
# Integration — resolve + forward citations for Attention Is All You Need
# ---------------------------------------------------------------------------

@integration
@pytest.mark.asyncio
async def test_resolve_attention_paper():
    from backend.agent.scholar import resolve_paper_ss

    result = await resolve_paper_ss("Attention Is All You Need")
    if result is None:
        pytest.skip("Semantic Scholar rate-limited during resolution — try again in a minute")

    ss_id, meta = result
    assert ss_id, "Should have a Semantic Scholar ID"
    assert meta["year"] == 2017, f"Expected 2017, got {meta['year']}"
    authors_lower = " ".join(meta["authors"]).lower()
    assert "vaswani" in authors_lower, f"Expected Vaswani in authors, got {meta['authors']}"
    assert "Computer Science" in meta["fields_of_study"], \
        f"Expected Computer Science in fields, got {meta['fields_of_study']}"


@integration
@pytest.mark.asyncio
async def test_forward_citations_are_ml_related():
    from backend.agent.scholar import get_citing_papers, resolve_paper_ss

    result = await resolve_paper_ss("Attention Is All You Need")
    if result is None:
        pytest.skip("Semantic Scholar rate-limited — try again in a minute")
    ss_id, meta = result

    citing = await get_citing_papers(ss_id, meta["fields_of_study"], limit=20, top_k=10)
    assert len(citing) > 0, "Should find citing papers for the Transformer paper"

    cs_adjacent = {"computer science", "linguistics", "mathematics", "artificial intelligence"}
    for paper in citing:
        if paper.fields_of_study:
            paper_fields = {f.lower() for f in paper.fields_of_study}
            overlap = paper_fields & cs_adjacent
            assert overlap, (
                f"Non-CS paper slipped through: {paper.title!r} "
                f"fields={paper.fields_of_study}"
            )
