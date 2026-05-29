from __future__ import annotations

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from backend.config import get_settings
from backend.retrieval.retriever import Source

# Lazy-loaded — model is only fetched from HuggingFace on the first rerank call.
_tokenizer = None
_model = None


def _load() -> None:
    global _tokenizer, _model
    if _model is not None:
        return
    name = get_settings().reranker_model
    _tokenizer = AutoTokenizer.from_pretrained(name)
    # CPU-only: MPS doesn't support all ops required by the reranker.
    _model = AutoModelForSequenceClassification.from_pretrained(name)
    _model.eval()


def rerank(query: str, sources: list[Source], top_k: int) -> list[Source]:
    if not sources:
        return sources

    _load()

    pairs = [[query, s.content] for s in sources]
    inputs = _tokenizer(  # type: ignore[call-overload]
        pairs,
        padding=True,
        truncation=True,
        max_length=512,
        return_tensors="pt",
    )

    with torch.no_grad():
        scores = _model(**inputs).logits.squeeze(-1)  # type: ignore[operator]

    ranked = sorted(
        zip(sources, scores.tolist()),
        key=lambda x: x[1],
        reverse=True,
    )
    return [s for s, _ in ranked[:top_k]]
