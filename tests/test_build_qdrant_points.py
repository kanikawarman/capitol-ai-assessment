import pytest

from src.capitol_pipeline.pipeline import build_qdrant_points
from src.capitol_pipeline import pipeline as pipeline_mod
from src.capitol_pipeline import embeddings as embeddings_mod



def test_build_qdrant_points_empty_docs_returns_empty(monkeypatch):
    """
    If build_qdrant_points is called with an empty docs list, it should:
      - return []
      - NOT call embeddings.embed_texts
    """

    def exploding_embed_texts(*args, **kwargs):
        raise AssertionError("embed_texts should not be called for empty docs.")

    monkeypatch.setattr(pipeline_mod, "embed_texts", exploding_embed_texts)

    points = build_qdrant_points([])
    assert points == []


def test_build_qdrant_points_basic_mapping(monkeypatch):
    """
    Given transformed docs with text + metadata, build_qdrant_points should:
      - Call embed_texts once with the correct texts.
      - Produce Qdrant points where:
          * id == metadata['external_id']
          * payload contains text + metadata fields
          * vector == embedding returned by embed_texts
    """

    docs = [
        {
            "text": "First document text",
            "metadata": {
                "external_id": "doc-1",
                "title": "Title 1",
                "url": "http://example.com/1",
                "website": "example",
            },
        },
        {
            "text": "Second document text",
            "metadata": {
                "external_id": "doc-2",
                "title": "Title 2",
                "url": "http://example.com/2",
                "website": "example",
            },
        },
    ]

    captured_inputs = {}

    def fake_embed_texts(texts, model=embeddings_mod.EMBEDDING_MODEL, batch_size=50):
        # record what was passed in
        captured_inputs["texts"] = list(texts)
        captured_inputs["model"] = model
        # return deterministic fake vectors
        return [
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6],
        ]

    monkeypatch.setattr(pipeline_mod, "embed_texts", fake_embed_texts)

    points = build_qdrant_points(docs)

    # 1) embed_texts was called with the correct args
    assert captured_inputs["texts"] == [
        "First document text",
        "Second document text",
    ]
    assert captured_inputs["model"] == embeddings_mod.EMBEDDING_MODEL

    # 2) Length / count
    assert len(points) == 2

    p1, p2 = points

    # 3) IDs come from metadata.external_id
    assert p1["id"] == "doc-1"
    assert p2["id"] == "doc-2"
    assert isinstance(p1["id"], str)
    assert isinstance(p2["id"], str)

    # 4) Payload structure
    for doc, point in zip(docs, points):
        payload = point["payload"]
        assert isinstance(payload, dict)

        # text is present & correct
        assert payload["text"] == doc["text"]
        assert isinstance(payload["text"], str)

        # metadata keys are merged into payload
        for k, v in doc["metadata"].items():
            assert payload[k] == v

        # external_id in metadata is preserved
        assert payload["external_id"] == doc["metadata"]["external_id"]

    # 5) Vectors match fake embeddings
    assert points[0]["vector"] == [0.1, 0.2, 0.3]
    assert points[1]["vector"] == [0.4, 0.5, 0.6]


def test_build_qdrant_points_vector_dim_and_types(monkeypatch):
    """
    Sanity-check:
      - number of points == number of docs
      - each point['vector'] has the expected dimension
      - payload is dict and text is str
    """

    docs = [
        {
            "text": f"Doc {i} text",
            "metadata": {
                "external_id": f"doc-{i}",
                "title": f"Title {i}",
                "url": f"http://example.com/{i}",
            },
        }
        for i in range(3)
    ]

    dim = 5
    fake_vectors = [
        [float(i)] * dim for i in range(len(docs))
    ]  # 3 vectors, each of length 5

    def fake_embed_texts(texts, model=embeddings_mod.EMBEDDING_MODEL, batch_size=50):
        assert len(texts) == len(docs)
        return fake_vectors

    monkeypatch.setattr(pipeline_mod, "embed_texts", fake_embed_texts)

    points = build_qdrant_points(docs)

    assert len(points) == len(docs)

    for point in points:
        # type checks
        assert isinstance(point["id"], str)
        assert isinstance(point["payload"], dict)
        assert isinstance(point["payload"]["text"], str)

        # vector dim check
        vec = point["vector"]
        assert isinstance(vec, list)
        assert len(vec) == dim
