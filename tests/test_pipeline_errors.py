# tests/test_pipeline_errors.py

import json
from pathlib import Path

import pytest

import src.run_pipeline as run_pipeline
import src.capitol_pipeline.embeddings as embeddings
import src.capitol_pipeline.pipeline as pipeline_mod

def test_pipeline_missing_input_file_exits_nonzero(tmp_path: Path):
    """
    If the input file does not exist, the CLI should fail with a non-zero
    exit code and not silently succeed.
    """
    missing_input = tmp_path / "does_not_exist.json"
    output_dir = tmp_path / "output"

    # Call the CLI entrypoint directly with custom args
    exit_code = run_pipeline.main(
        [
            "--input",
            str(missing_input),
            "--output-dir",
            str(output_dir),
        ]
    )

    assert exit_code != 0
    # Optional: ensure we didn't accidentally create output files
    if output_dir.exists():
        assert len(list(output_dir.iterdir())) == 0


def test_pipeline_empty_input_file_succeeds_with_zero_docs(tmp_path: Path):
    """
    When the input file is an empty JSON array, the pipeline should:
      - return exit code 0
      - create an output file
      - write an empty list (no points).
    """
    input_path = tmp_path / "empty_input.json"
    output_dir = tmp_path / "output"

    # Simulate empty data source
    input_path.write_text("[]", encoding="utf-8")

    exit_code = run_pipeline.main(
        [
            "--input",
            str(input_path),
            "--output-dir",
            str(output_dir),
            "--skip-embeddings",  # Skip embeddings for empty data
        ]
    )

    assert exit_code == 0, "Empty input should be treated as successful."

    # Check that transformed documents file was created
    transformed_files = list(output_dir.glob("transformed*.json"))
    assert len(transformed_files) > 0, "Should create transformed documents file"

    # Read the transformed documents (not points, since we skip embeddings for empty data)
    transformed_path = transformed_files[0]
    data = json.loads(transformed_path.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert len(data) == 0

def test_pipeline_openai_api_error_fails_fast(tmp_path: Path, monkeypatch):
    """
    If the OpenAI embeddings call fails in the middle, the pipeline CLI should:
      - exit with a non-zero code
      - not silently succeed
      - ideally not leave a partial output file behind.
    """

    # 1) Prepare a small valid input file with a couple of docs
    input_path = tmp_path / "input.json"
    docs = [
        {
            "external_id": "doc-1",
            "title": "Doc 1",
            "url": "http://example.com/1",
            "text": "First document text",
        },
        {
            "external_id": "doc-2",
            "title": "Doc 2",
            "url": "http://example.com/2",
            "text": "Second document text",
        },
    ]
    input_path.write_text(json.dumps(docs), encoding="utf-8")

    output_dir = tmp_path / "output"

    # 2) Monkeypatch the build_qdrant_points step to simulate an embedding error
    def fake_build_qdrant_points(*args, **kwargs):
        raise RuntimeError("Simulated OpenAI API error  / embedding step error")

    monkeypatch.setattr(
        pipeline_mod,
        "build_qdrant_points",
        fake_build_qdrant_points,
    )

    # 3) Run the CLI
    exit_code = run_pipeline.main(
        [
            "--input",
            str(input_path),
            "--output-dir",
            str(output_dir),
        ]
    )

    # 4) Assert behavior
    assert exit_code != 0, "Pipeline should fail (non-zero exit) on OpenAI API error."
    # Don't leave half-written files behind - transformed file may exist but not points file
    if output_dir.exists():
        points_files = list(output_dir.glob("qdrant_points*.json"))
        assert len(points_files) == 0, "Output file should not exist on hard failure."

def test_pipeline_unwritable_output_path_returns_error(tmp_path: Path):
    """
    If the output directory is not writable (e.g., read-only),
    the pipeline should:
      - exit with a non-zero code
      - not silently succeed.
    """
    input_path = tmp_path / "input.json"
    docs = [
        {
            "external_id": "doc-1",
            "title": "Doc 1",
            "url": "http://example.com/1",
            "text": "Some text",
        }
    ]
    input_path.write_text(json.dumps(docs), encoding="utf-8")

    # Create a read-only directory
    output_dir = tmp_path / "readonly_output"
    output_dir.mkdir()
    output_dir.chmod(0o444)  # Read-only for all

    try:
        exit_code = run_pipeline.main(
            [
                "--input",
                str(input_path),
                "--output-dir",
                str(output_dir),
            ]
        )

        assert exit_code != 0, "Pipeline should fail when output path is not writable."
    finally:
        # Restore write permissions for cleanup
        output_dir.chmod(0o755)


