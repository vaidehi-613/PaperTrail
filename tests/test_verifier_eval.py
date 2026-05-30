import json
import pytest

from backend.agent.scholar import ScholarResult
from backend.verifier.checks import verify_scholar_results


def load_eval_data():
    """Load the labeled evaluation dataset."""
    with open("tests/data/verifier_eval.json") as f:
        return json.load(f)


@pytest.mark.asyncio
async def test_verifier_eval(monkeypatch):
    """
    Comprehensive verifier evaluation measuring precision/recall on catching fabricated citations.

    Test set: 20 cases
    - 8 verified (real papers, claims supported)
    - 6 not_found (fabricated papers)
    - 6 flagged (real papers, but claims contradicted by abstract)
    """
    cases = load_eval_data()

    # Create mock functions that route based on case ground_truth
    # We'll use a closure to access the current case during mocking
    current_case = {"data": None}

    async def mock_resolve_paper_oa(title):
        """Mock resolve based on current case ground_truth."""
        case = current_case["data"]
        if case["ground_truth"] == "not_found":
            return None
        else:
            # Return fake OpenAlex metadata for verified/flagged cases
            return (
                "https://openalex.org/W123456",
                {
                    "title": case["scholar_result"]["title"],
                    "doi": case["scholar_result"].get("doi"),
                    "authors": case["scholar_result"]["authors"],
                    "year": case["scholar_result"]["year"],
                }
            )

    async def mock_fetch_is_retracted(oa_id):
        """No retractions in eval set."""
        return False

    class FakeLLM:
        """Mock LLM for claim support checking."""
        def __init__(self, **kwargs):
            pass

        async def ainvoke(self, prompt):
            """Return SUPPORTED for verified, REFUTED for flagged."""
            case = current_case["data"]

            class FakeResponse:
                def __init__(self, verdict):
                    self.content = verdict

            if case["ground_truth"] == "flagged":
                return FakeResponse("REFUTED - The claim contradicts the abstract.")
            else:
                return FakeResponse("SUPPORTED - The claim is consistent with the abstract.")

    # Patch the dependencies
    monkeypatch.setattr("backend.verifier.checks.resolve_paper_oa", mock_resolve_paper_oa)
    monkeypatch.setattr("backend.verifier.checks._fetch_is_retracted", mock_fetch_is_retracted)
    monkeypatch.setattr("backend.verifier.checks.ChatOpenAI", FakeLLM)

    # Run verifier on each case
    results = []
    for case in cases:
        current_case["data"] = case  # Set current case for mocks

        # Convert to ScholarResult
        scholar_result = ScholarResult(**case["scholar_result"])

        # Run verifier
        verifications = await verify_scholar_results(
            case["answer"],
            [scholar_result]
        )

        predicted = verifications[0].status
        actual = case["ground_truth"]

        results.append({
            "title": case["scholar_result"]["title"][:50],
            "predicted": predicted,
            "actual": actual,
            "match": predicted == actual
        })

    # Calculate precision/recall metrics
    # True Positive: correctly identified as fake (predicted in {not_found, flagged}, actual in {not_found, flagged})
    # False Positive: incorrectly flagged as fake (predicted in {not_found, flagged}, actual = verified)
    # False Negative: missed a fake (predicted = verified, actual in {not_found, flagged})

    tp = sum(1 for r in results if r["predicted"] in ("not_found", "flagged") and r["actual"] in ("not_found", "flagged"))
    fp = sum(1 for r in results if r["predicted"] in ("not_found", "flagged") and r["actual"] == "verified")
    fn = sum(1 for r in results if r["predicted"] == "verified" and r["actual"] in ("not_found", "flagged"))
    tn = sum(1 for r in results if r["predicted"] == "verified" and r["actual"] == "verified")

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    accuracy = (tp + tn) / len(results) if results else 0

    # Print detailed results
    print("\n" + "=" * 80)
    print("VERIFIER EVALUATION RESULTS")
    print("=" * 80)
    print(f"\nTest Set Size: {len(cases)} cases")
    print(f"  - Verified (real + supported): {sum(1 for c in cases if c['ground_truth'] == 'verified')}")
    print(f"  - Not Found (fabricated): {sum(1 for c in cases if c['ground_truth'] == 'not_found')}")
    print(f"  - Flagged (real + contradicted): {sum(1 for c in cases if c['ground_truth'] == 'flagged')}")

    print(f"\nConfusion Matrix:")
    print(f"  True Positives (correctly caught fakes):  {tp}")
    print(f"  False Positives (real flagged as fake):   {fp}")
    print(f"  False Negatives (fakes missed):           {fn}")
    print(f"  True Negatives (real verified correctly): {tn}")

    print(f"\nMetrics:")
    print(f"  Precision: {precision:.1%}  (of flagged, % actually fake)")
    print(f"  Recall:    {recall:.1%}  (of fakes, % caught)")
    print(f"  F1 Score:  {f1:.1%}")
    print(f"  Accuracy:  {accuracy:.1%}")

    print(f"\nPer-Case Results:")
    print(f"{'Title':<52} {'Predicted':<12} {'Actual':<12} {'Match'}")
    print("-" * 80)
    for r in results:
        match_sym = "✓" if r["match"] else "✗"
        print(f"{r['title']:<52} {r['predicted']:<12} {r['actual']:<12} {match_sym}")

    print("=" * 80 + "\n")

    # Assertions - require strong performance
    assert precision >= 0.85, f"Precision {precision:.1%} below 85% threshold"
    assert recall >= 0.85, f"Recall {recall:.1%} below 85% threshold"
    assert f1 >= 0.85, f"F1 {f1:.1%} below 85% threshold"

    # All predictions should match ground truth (perfect accuracy expected with mocking)
    mismatches = [r for r in results if not r["match"]]
    assert len(mismatches) == 0, f"Found {len(mismatches)} prediction mismatches: {mismatches}"
