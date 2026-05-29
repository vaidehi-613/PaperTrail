import re


def extract_claim_for_paper(answer: str, paper_title: str) -> str:
    """
    Return the sentence(s) in answer that mention paper_title.
    Falls back to the full answer if nothing matches.
    """
    sentences = re.split(r"(?<=[.!?])\s+", answer.strip())
    title_lower = paper_title.lower()
    # Use significant words only (skip very short words)
    keywords = [w for w in title_lower.split() if len(w) > 3]

    matching = [
        s for s in sentences
        if any(kw in s.lower() for kw in keywords)
    ]
    return " ".join(matching) if matching else answer
