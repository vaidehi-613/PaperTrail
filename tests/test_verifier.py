import pytest

from backend.agent.scholar import ScholarResult
from backend.verifier.checks import VerificationResult, check_claim_support, check_existence, verify_scholar_results
from backend.verifier.extractor import extract_claim_for_paper


# ---------------------------------------------------------------------------
# Unit — extractor
# ---------------------------------------------------------------------------

def test_extract_claim_simple():
    answer = "The paper introduces BERT. BERT uses masked language modeling. It achieves SOTA."
    claim = extract_claim_for_paper(answer, "BERT")
    assert "BERT" in claim
    # Should extract sentences mentioning BERT
    assert "masked language modeling" in claim or "introduces BERT" in claim


def test_extract_claim_no_match_fallback():
    answer = "The model uses self-attention."
    claim = extract_claim_for_paper(answer, "Some Other Paper Title")
    # Falls back to full answer
    assert claim == answer


# ---------------------------------------------------------------------------
# Unit — check_existence (mocked)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_check_existence_found(monkeypatch):
    """Mock resolve_paper_oa → returns real meta → status=verified"""

    async def fake_resolve(title):
        return (
            "https://openalex.org/W123",
            {"doi": "10.1234/test", "is_retracted": False}
        )

    async def fake_fetch_retracted(oa_id):
        return False

    monkeypatch.setattr("backend.verifier.checks.resolve_paper_oa", fake_resolve)
    monkeypatch.setattr("backend.verifier.checks._fetch_is_retracted", fake_fetch_retracted)

    result = await check_existence("Test Paper", ["Author A"])
    assert result.status == "verified"
    assert result.doi == "10.1234/test"


@pytest.mark.asyncio
async def test_check_existence_not_found(monkeypatch):
    """Mock resolve_paper_oa → returns None → status=not_found"""

    async def fake_resolve(title):
        return None

    monkeypatch.setattr("backend.verifier.checks.resolve_paper_oa", fake_resolve)

    result = await check_existence("Fake Paper", ["Author B"])
    assert result.status == "not_found"
    assert result.doi is None


@pytest.mark.asyncio
async def test_check_retracted(monkeypatch):
    """Mock OpenAlex returns is_retracted=True → status=retracted"""

    async def fake_resolve(title):
        return (
            "https://openalex.org/W456",
            {"doi": "10.1234/retracted", "is_retracted": False}
        )

    async def fake_fetch_retracted(oa_id):
        return True

    monkeypatch.setattr("backend.verifier.checks.resolve_paper_oa", fake_resolve)
    monkeypatch.setattr("backend.verifier.checks._fetch_is_retracted", fake_fetch_retracted)

    result = await check_existence("Retracted Paper", ["Author C"])
    assert result.status == "retracted"
    assert "retracted" in result.note.lower()


# ---------------------------------------------------------------------------
# Unit — check_claim_support (mocked)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_claim_support_supported(monkeypatch):
    """Mock LLM returns SUPPORTED"""

    class FakeResponse:
        content = "SUPPORTED"

    class FakeLLM:
        async def ainvoke(self, prompt):
            return FakeResponse()

    monkeypatch.setattr("backend.verifier.checks.ChatOpenAI", lambda **_: FakeLLM())

    verdict = await check_claim_support("BERT uses MLM", "BERT is trained with masked language modeling.")
    assert verdict == "supported"


@pytest.mark.asyncio
async def test_claim_support_refuted(monkeypatch):
    """Mock LLM returns REFUTED → status=flagged"""

    class FakeResponse:
        content = "REFUTED"

    class FakeLLM:
        async def ainvoke(self, prompt):
            return FakeResponse()

    monkeypatch.setattr("backend.verifier.checks.ChatOpenAI", lambda **_: FakeLLM())

    verdict = await check_claim_support("BERT uses RNNs", "BERT uses transformers, not RNNs.")
    assert verdict == "refuted"


# ---------------------------------------------------------------------------
# Unit — verify_scholar_results (mocked)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_verify_scholar_results_verified(monkeypatch):
    """Full pipeline: paper exists, claim supported → verified"""

    async def fake_resolve(title):
        return ("https://openalex.org/W789", {"doi": "10.1234/good", "is_retracted": False})

    async def fake_fetch_retracted(oa_id):
        return False

    class FakeResponse:
        content = "SUPPORTED"

    class FakeLLM:
        async def ainvoke(self, prompt):
            return FakeResponse()

    monkeypatch.setattr("backend.verifier.checks.resolve_paper_oa", fake_resolve)
    monkeypatch.setattr("backend.verifier.checks._fetch_is_retracted", fake_fetch_retracted)
    monkeypatch.setattr("backend.verifier.checks.ChatOpenAI", lambda **_: FakeLLM())

    answer = "BERT uses masked language modeling."
    papers = [ScholarResult(
        title="BERT",
        authors=["Devlin"],
        year=2019,
        abstract="BERT uses MLM.",
        doi="10.1234/good",
        url="https://doi.org/10.1234/good"
    )]

    results = await verify_scholar_results(answer, papers)
    assert len(results) == 1
    assert results[0].status == "verified"


@pytest.mark.asyncio
async def test_verify_scholar_results_flagged(monkeypatch):
    """Full pipeline: paper exists, but claim refuted → flagged"""

    async def fake_resolve(title):
        return ("https://openalex.org/W999", {"doi": "10.1234/flag", "is_retracted": False})

    async def fake_fetch_retracted(oa_id):
        return False

    class FakeResponse:
        content = "REFUTED"

    class FakeLLM:
        async def ainvoke(self, prompt):
            return FakeResponse()

    monkeypatch.setattr("backend.verifier.checks.resolve_paper_oa", fake_resolve)
    monkeypatch.setattr("backend.verifier.checks._fetch_is_retracted", fake_fetch_retracted)
    monkeypatch.setattr("backend.verifier.checks.ChatOpenAI", lambda **_: FakeLLM())

    answer = "XYZ uses quantum encryption."
    papers = [ScholarResult(
        title="XYZ",
        authors=["Smith"],
        year=2020,
        abstract="XYZ uses classical RSA encryption.",
        doi="10.1234/flag",
        url="https://doi.org/10.1234/flag"
    )]

    results = await verify_scholar_results(answer, papers)
    assert len(results) == 1
    assert results[0].status == "flagged"
    assert "does not" in results[0].note.lower()
