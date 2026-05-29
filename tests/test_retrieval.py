import pytest

from backend.retrieval.retriever import Source, retrieve

# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

FAKE_EMBEDDING = [0.1] * 1536
FAKE_ROW = {
    "id": "chunk-abc",
    "content": "The BERT model uses masked language modelling.",
    "section": "Methods",
    "page": 4,
    "is_table": False,
    "is_figure": False,
    "similarity": 0.031,
}


class _FakeEmbeddingData:
    embedding = FAKE_EMBEDDING


class _FakeEmbeddingResponse:
    data = [_FakeEmbeddingData()]


class _FakeEmbeddings:
    async def create(self, **_kwargs):
        return _FakeEmbeddingResponse()


class _FakeOpenAI:
    embeddings = _FakeEmbeddings()

    def __init__(self, **_kwargs):
        pass


class _FakeRPC:
    def __init__(self):
        self.last_fn: str = ""
        self.last_params: dict = {}

    def __call__(self, fn_name: str, params: dict):
        self.last_fn = fn_name
        self.last_params = params
        return self

    async def execute(self):
        class _Result:
            data = [FAKE_ROW]

        return _Result()


class _FakeSupabase:
    def __init__(self):
        self.rpc = _FakeRPC()


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retrieve_calls_hybrid_rpc(monkeypatch) -> None:
    """retrieve() must call match_chunks_hybrid with both vector + text params."""
    fake_sb = _FakeSupabase()

    async def fake_get_supabase():
        return fake_sb

    monkeypatch.setattr("backend.retrieval.retriever.AsyncOpenAI", _FakeOpenAI)
    monkeypatch.setattr("backend.retrieval.retriever.get_supabase", fake_get_supabase)

    results = await retrieve("masked language modelling", "paper-xyz")

    # Correct RPC name
    assert fake_sb.rpc.last_fn == "match_chunks_hybrid"

    # Both retrieval signals present
    params = fake_sb.rpc.last_params
    assert "query_embedding" in params
    assert params["query_text"] == "masked language modelling"
    assert params["filter_paper_id"] == "paper-xyz"
    assert "match_count" in params
    assert "rrf_k" in params

    # Result shape
    assert len(results) == 1
    src = results[0]
    assert isinstance(src, Source)
    assert src.content == FAKE_ROW["content"]
    assert src.section == "Methods"
    assert src.page == 4
