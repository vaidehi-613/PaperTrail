from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal

import httpx
from langchain_openai import ChatOpenAI

from backend.agent.scholar import ScholarResult, resolve_paper_oa
from backend.config import get_settings
from backend.verifier.extractor import extract_claim_for_paper

logger = logging.getLogger(__name__)

_OA_BASE = "https://api.openalex.org"
_OA_HEADERS = {"User-Agent": "PaperTrail/1.0 (mailto:papertrail@example.com)"}

ClaimVerdict = Literal["supported", "refuted", "uncertain"]


@dataclass
class VerificationResult:
    title: str
    status: Literal["verified", "flagged", "not_found", "retracted"]
    doi: str | None
    url: str | None
    note: str | None


async def _fetch_is_retracted(oa_work_id: str) -> bool:
    """Fetch the is_retracted flag for an OpenAlex Work ID."""
    short_id = oa_work_id.split("/")[-1]  # "W2963403153"
    url = f"{_OA_BASE}/works/{short_id}"
    async with httpx.AsyncClient(timeout=10, headers=_OA_HEADERS) as client:
        resp = await client.get(url, params={"select": "id,is_retracted"})
    if resp.status_code != 200:
        return False
    return bool(resp.json().get("is_retracted", False))


async def check_existence(
    title: str,
    authors: list[str] | None = None,
) -> VerificationResult:
    """
    Check whether a paper title resolves to a real OpenAlex entry.
    Also checks the retraction flag on the resolved work.
    """
    logger.info("[verifier] check_existence  title=%r", title)
    resolved = await resolve_paper_oa(title)

    if resolved is None:
        logger.info("[verifier] NOT FOUND  title=%r", title)
        return VerificationResult(
            title=title,
            status="not_found",
            doi=None,
            url=None,
            note="Could not find this paper in OpenAlex.",
        )

    oa_id, meta = resolved
    doi = meta.get("doi")
    url = f"https://doi.org/{doi}" if doi else oa_id

    is_retracted = await _fetch_is_retracted(oa_id)
    if is_retracted:
        logger.warning("[verifier] RETRACTED  title=%r  oa_id=%s", title, oa_id)
        return VerificationResult(
            title=title,
            status="retracted",
            doi=doi,
            url=url,
            note="This paper has been retracted.",
        )

    logger.info("[verifier] VERIFIED  title=%r  oa_id=%s  doi=%s", title, oa_id, doi)
    return VerificationResult(
        title=title,
        status="verified",
        doi=doi,
        url=url,
        note=None,
    )


async def check_claim_support(claim: str, abstract: str) -> ClaimVerdict:
    """
    LLM-as-judge: does the abstract support the claim?
    Returns 'supported', 'refuted', or 'uncertain'.
    """
    if not abstract or not claim:
        return "uncertain"

    settings = get_settings()
    llm = ChatOpenAI(model=settings.llm_model, api_key=settings.openai_api_key)

    prompt = (
        "You are a scientific fact-checker.\n"
        f"Abstract: {abstract[:1000]}\n\n"
        f"Claim: {claim}\n\n"
        "Does the abstract SUPPORT, REFUTE, or give UNCERTAIN evidence for the claim? "
        "Reply with exactly one word: SUPPORTED, REFUTED, or UNCERTAIN."
    )
    response = await llm.ainvoke(prompt)
    verdict = response.content.strip().upper().split()[0]

    if "REFUTED" in verdict:
        return "refuted"
    if "SUPPORTED" in verdict:
        return "supported"
    return "uncertain"


async def verify_scholar_results(
    answer: str,
    scholar_results: list[ScholarResult],
) -> list[VerificationResult]:
    """
    Run all three checks for each ScholarResult and return VerificationResult list.
    Runs checks concurrently where possible.
    """
    import asyncio

    async def _verify_one(paper: ScholarResult) -> VerificationResult:
        # Check 1 + 2: existence + retraction
        result = await check_existence(paper.title, paper.authors)

        # Check 3: claim support (only if verified and abstract available)
        if result.status == "verified" and paper.abstract:
            claim = extract_claim_for_paper(answer, paper.title)
            verdict = await check_claim_support(claim, paper.abstract)
            if verdict == "refuted":
                result.status = "flagged"
                result.note = "The abstract does not clearly support the agent's claim."
                logger.warning("[verifier] FLAGGED  title=%r  claim=%r", paper.title, claim[:80])

        return result

    return list(await asyncio.gather(*[_verify_one(p) for p in scholar_results]))
