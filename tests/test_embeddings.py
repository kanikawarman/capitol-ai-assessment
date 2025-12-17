import pytest
from src.capitol_pipeline import embeddings


class DummyEmbeddingItem:
    def __init__(self, vec):
        self.embedding = vec


class DummyResponse:
    def __init__(self, vectors):
        self.data = [DummyEmbeddingItem(v) for v in vectors]


class RecordingClient:
    """
    Fake OpenAI client that records calls to embeddings.create
    and returns configurable responses.
    """
    def __init__(self, responses):
        """
        responses: List of lists-of-vectors, one per call.
        Example: [
          [[1.0, 2.0], [3.0, 4.0]],   # first create() returns 2 vectors
          [[5.0, 6.0]]                # second create() returns 1 vector
        ]
        """
        self.responses = list(responses)
        self.calls = []

        class _Embeddings:
            def __init__(self, outer):
                self._outer = outer

            def create(self, model, input):
                # Record the call
                self._outer.calls.append({
                    "model": model,
                    "input": input,
                })
                if not self._outer.responses:
                    raise RuntimeError("No more fake responses configured")
                vectors = self._outer.responses.pop(0)
                return DummyResponse(vectors)

        self.embeddings = _Embeddings(self)


def test_embed_texts_empty_returns_empty(monkeypatch):
    """
    Empty input list should return [] without calling the OpenAI client.
    """
    class ExplodingClient:
        class _Embeddings:
            def create(self, *args, **kwargs):
                raise AssertionError(
                    "embeddings.create should not be called for empty input"
                )
        embeddings = _Embeddings()

    monkeypatch.setattr(embeddings, "client", ExplodingClient())

    result = embeddings.embed_texts([])
    assert result == []


def test_embedding_single_batch_correct_dim(monkeypatch):
    """
    Given N texts, embed_texts should return N vectors of consistent dimension
    and call the API once when batch_size >= N.
    """
    fake_client = RecordingClient(
        responses=[
            # First (and only) call -> 3 vectors of dim=4
            [
                [0.1, 0.2, 0.3, 0.4],
                [0.5, 0.6, 0.7, 0.8],
                [0.9, 1.0, 1.1, 1.2],
            ]
        ]
    )
    monkeypatch.setattr(embeddings, "client", fake_client)

    texts = ["a", "b", "c"]
    vectors = embeddings.embed_texts(texts, batch_size=10)

    assert len(vectors) == 3
    assert all(len(v) == 4 for v in vectors)

    # One API call with all 3 inputs in a single batch
    assert len(fake_client.calls) == 1
    call = fake_client.calls[0]
    assert call["input"] == texts
    assert call["model"] == embeddings.EMBEDDING_MODEL


def test_embedding_batch_size_respected(monkeypatch):
    """
    Given N texts and batch_size=K, embed_texts should call the API
    ceil(N / K) times with batches of size at most K.
    """
    fake_client = RecordingClient(
        responses=[
            [[0.0, 0.1]],  # Response for first call
            [[0.2, 0.3]],  # Second
            [[0.4, 0.5]],  # Third
        ]
    )
    monkeypatch.setattr(embeddings, "client", fake_client)

    texts = ["t1", "t2", "t3", "t4", "t5"]
    _ = embeddings.embed_texts(texts, batch_size=2)

    # 5 texts, batch_size=2 -> 3 calls: [t1,t2], [t3,t4], [t5]
    assert len(fake_client.calls) == 3
    batch_sizes = [len(c["input"]) for c in fake_client.calls]
    assert batch_sizes == [2, 2, 1]


def test_embedding_raises_on_inconsistent_dim(monkeypatch):
    """
    If API returns vectors of different dimensionality, embed_texts should raise.
    """
    fake_client = RecordingClient(
        responses=[
            # First vector dim=3, second dim=2 -> inconsistent
            [
                [0.1, 0.2, 0.3],
                [0.4, 0.5],
            ]
        ]
    )
    monkeypatch.setattr(embeddings, "client", fake_client)

    with pytest.raises(ValueError, match="Inconsistent embedding dimension"):
        embeddings.embed_texts(["a", "b"], batch_size=10)


def test_embedding_handles_api_error_gracefully(monkeypatch):
    """
    If the OpenAI client raises (e.g. timeout/500), embed_texts should
    re-raise the exception.
    """
    class ErrorClient:
        class _Embeddings:
            def create(self, *args, **kwargs):
                raise RuntimeError("Simulated API failure")
        embeddings = _Embeddings()

    monkeypatch.setattr(embeddings, "client", ErrorClient())

    with pytest.raises(RuntimeError, match="Simulated API failure"):
        embeddings.embed_texts(["a", "b"])


def test_embed_texts_truncates_long_text(monkeypatch):
    """
    Very long texts should be automatically truncated to MAX_EMBEDDING_CHARS
    before being sent to the API.
    """
    # Create fake response for the truncated text
    fake_client = RecordingClient(
        responses=[
            [[0.1, 0.2, 0.3, 0.4]]  # Single vector response
        ]
    )
    monkeypatch.setattr(embeddings, "client", fake_client)
    
    # Create text that exceeds MAX_EMBEDDING_CHARS (default 8000)
    very_long_text = "x" * 20000  # 20k characters
    
    vectors = embeddings.embed_texts([very_long_text])
    
    # Should succeed (not raise)
    assert len(vectors) == 1
    assert len(vectors[0]) == 4
    
    # Verify the text sent to API was truncated
    assert len(fake_client.calls) == 1
    sent_text = fake_client.calls[0]["input"][0]
    assert len(sent_text) <= embeddings.MAX_EMBEDDING_CHARS
