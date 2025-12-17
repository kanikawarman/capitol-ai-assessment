# tests/test_pipeline_integration.py

import json
import logging
from pathlib import Path

import pytest

from src.capitol_pipeline import pipeline as pipeline_mod
from src.capitol_pipeline import embeddings as embeddings_mod
import src.run_pipeline as run_pipeline_cli


def test_pipeline_creates_valid_qdrant_points_for_small_input(tmp_path: Path, monkeypatch):
    """
    End-to-end happy path integration test.

    - Use a tiny input JSON file (2 docs).
    - Monkeypatch embeddings to avoid real OpenAI calls.
    - Run the pipeline function (not CLI).
    - Assert:
        * processed == number of raw docs
        * produced == number of points
        * output file exists and has correct length
        * each point has id, vector, payload, payload.external_id, payload.text.
    """
    # 1) Prepare a small valid input file
    docs = [
        {
            "_id": "doc-1",  # real API style
            "title": "First article",
            "url": "http://example.com/1",
            "website": "example",
            "content_elements": [
                {"type": "text", "content": "First document text"},
            ],
        },
        {
            "_id": "doc-2",
            "title": "Second article",
            "url": "http://example.com/2",
            "website": "example",
            "content_elements": [
                {"type": "text", "content": "Second document text"},
            ],
        },
    ]

    input_path = tmp_path / "small_input.json"
    output_dir = tmp_path / "output"
    input_path.write_text(json.dumps(docs), encoding="utf-8")

    # 2) Monkeypatch embeddings so we don't hit the real API
    dim = 4
    fake_vectors = [
        [0.1, 0.2, 0.3, 0.4],
        [0.5, 0.6, 0.7, 0.8],
    ]

    def fake_embed_texts(texts, model=embeddings_mod.EMBEDDING_MODEL, **kwargs):
        # basic sanity: we should be embedding one vector per doc
        assert len(texts) == len(docs)
        # Each text should be a non-empty string
        assert all(isinstance(t, str) and t.strip() for t in texts)
        return fake_vectors

    # NOTE: patch on the pipeline module, because build_qdrant_points imports embed_texts there
    monkeypatch.setattr(pipeline_mod, "embed_texts", fake_embed_texts)

    # 3) Run the pipeline function end-to-end
    total_raw, processed_count, output_paths = pipeline_mod.run_pipeline(
        input_path=input_path,
        output_dir=output_dir,
        limit=None,
        keep_history=False,
    )

    # 4) Assert counts & output file existence
    assert total_raw == len(docs)
    assert processed_count == len(docs)
    points_path = output_paths["points"]
    assert points_path.exists()

    # 5) Validate the written Qdrant points
    points = json.loads(points_path.read_text(encoding="utf-8"))
    assert isinstance(points, list)
    assert len(points) == len(docs)

    for raw_doc, point, expected_vec in zip(docs, points, fake_vectors):
        # id should come from the API _id (our external_id source of truth)
        expected_id = str(raw_doc["_id"])
        assert point["id"] == expected_id

        # vector wiring & dimension
        vec = point["vector"]
        assert isinstance(vec, list)
        assert vec == expected_vec
        assert len(vec) == dim

        # payload shape
        payload = point["payload"]
        assert isinstance(payload, dict)

        # text
        assert "text" in payload
        assert isinstance(payload["text"], str)
        assert payload["text"].strip()  # non-empty

        # external_id from metadata must match point id
        assert payload["external_id"] == expected_id

        # url should be preserved from raw doc
        assert payload["url"] == raw_doc["url"]

def test_pipeline_logging_high_level_messages(tmp_path: Path, monkeypatch, capsys):
    """
    Integration test for logging at INFO level.

    - Use the CLI entrypoint (run_pipeline.main) so we exercise the script as it
      would be run in production.
    - Monkeypatch embeddings to avoid real API calls.
    - Capture logs and assert that our high-level milestones appear.
    """
    # 1) Tiny valid input file
    docs = [
        {
            "_id": "doc-1",
            "title": "Logging test article",
            "url": "http://example.com/log",
            "website": "example",
            "content_elements": [
                {"type": "text", "content": "Some logging test text."},
            ],
        }
    ]
    input_path = tmp_path / "logging_input.json"
    output_dir = tmp_path / "output"
    input_path.write_text(json.dumps(docs), encoding="utf-8")

    # 2) Monkeypatch embeddings (no network)
    def fake_embed_texts(texts, model=embeddings_mod.EMBEDDING_MODEL,  **kwargs):
        # one vector per text, simple dim=3
        return [[0.0, 0.0, 0.0] for _ in texts]

    monkeypatch.setattr(pipeline_mod, "embed_texts", fake_embed_texts)

    # 3) Run the CLI: python run_pipeline.py --input ... --output-dir ...
    exit_code = run_pipeline_cli.main(
        [
            "--input",
            str(input_path),
            "--output-dir",
            str(output_dir),
            "--no-history",
        ]
    )

    assert exit_code == 0
    # Check that output files were created in the output directory
    points_file = output_dir / "qdrant_points.json"
    assert points_file.exists()

    # 4) Capture stderr/stdout after the run
    captured = capsys.readouterr()
    # Our logging.StreamHandler writes to stderr by default
    messages = captured.err

    # 5) Check that the expected high-level log messages are present
    assert "=== Starting Capitol AI ingestion pipeline ===" in messages
    assert "STEP 1/5: Loading raw documents" in messages
    assert "STEP 2/5: Transforming" in messages
    assert "Processing" in messages and "batch" in messages  # Embedding batch processing
    assert "Pipeline completed successfully" in messages


def test_pipeline_skips_duplicate_external_id_and_logs_warning(tmp_path: Path, monkeypatch, caplog):
    """
    If two raw docs share the same external_id/_id, the pipeline should:
      - keep only the first occurrence
      - skip the duplicate
      - log a warning
      - produce exactly one Qdrant point in the output.
    """
    # 1) Two docs with the same _id (source of truth for external_id)
    docs = [
        {
            "_id": "dup-1",
            "title": "First version",
            "url": "http://example.com/dup",
            "website": "example",
            "content_elements": [
                {"type": "text", "content": "First doc body."},
            ],
        },
        {
            "_id": "dup-1",  # duplicate external_id
            "title": "Second version",
            "url": "http://example.com/dup-2",
            "website": "example",
            "content_elements": [
                {"type": "text", "content": "Second doc body."},
            ],
        },
    ]

    input_path = tmp_path / "dup_input.json"
    output_dir = tmp_path / "output"
    input_path.write_text(json.dumps(docs), encoding="utf-8")

    # 2) Fake embeddings: one vector per text; we expect to be called ONCE
    def fake_embed_texts(texts, model=embeddings_mod.EMBEDDING_MODEL,  **kwargs):
        # After dedupe there should be only 1 text
        assert len(texts) == 1
        return [[0.1, 0.2, 0.3]]

    monkeypatch.setattr(pipeline_mod, "embed_texts", fake_embed_texts)

    caplog.set_level(logging.WARNING)

    # 3) Run pipeline directly (function, not CLI) so we get return counts
    total_raw, processed_count, output_paths = pipeline_mod.run_pipeline(
        input_path=input_path,
        output_dir=output_dir,
        limit=None,
        keep_history=False,
    )

    # 4) Assertions
    assert total_raw == 2
    assert processed_count == 1
    points_path = output_paths["points"]
    assert points_path.exists()

    points = json.loads(points_path.read_text(encoding="utf-8"))
    assert isinstance(points, list)
    assert len(points) == 1

    point = points[0]
    assert point["id"] == "dup-1"
    assert point["payload"]["external_id"] == "dup-1"

    # 5) We logged a warning about duplicate external_id
    messages = "\n".join(rec.getMessage() for rec in caplog.records)
    assert "Duplicate external_id detected" in messages
