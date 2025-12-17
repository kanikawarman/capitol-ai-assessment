import json
from pathlib import Path

import logging
import pytest

from src.capitol_pipeline import pipeline as pipeline_mod
from src.capitol_pipeline.scripts import validate_output as validate_script
import src.run_pipeline as run_pipeline_cli


def test_pipeline_and_validation_on_fixture(tmp_path, monkeypatch, capsys):
    """
    Full integration:
      - run the pipeline CLI on a small fixture file
      - run validate_output.py against the produced file
      - assert both succeed
    """
    # 1) Copy fixture into tmp_path
    fixture_src = Path("tests/fixtures/raw_small.json")
    fixture_dst = tmp_path / "raw_small.json"
    fixture_dst.write_text(fixture_src.read_text(encoding="utf-8"), encoding="utf-8")

    output_path = tmp_path / "points_with_embeddings.json"

    # 2) Monkeypatch embeddings to avoid real OpenAI calls
    def fake_embed_texts(texts, model=pipeline_mod.embed_texts.__defaults__[0], batch_size=50):
        # simple deterministic vectors, dim=3
        return [[1.0, 0.0, 0.0] for _ in texts]

    monkeypatch.setattr(pipeline_mod, "embed_texts", fake_embed_texts)

    # 3) Run the pipeline CLI
    exit_code = run_pipeline_cli.main(
        [
            "--input",
            str(fixture_dst),
            "--output-dir",
            str(output_path),
        ]
    )
    assert exit_code == 0
    assert output_path.exists()

    # 4) Find the generated points file (it will have a timestamp)
    points_files = list(output_path.glob("qdrant_points_*.json"))
    assert len(points_files) > 0, "No qdrant_points file generated"
    points_file = points_files[0]

    # 5) Run validation script on the output (expected_dim=3 from fake vectors)
    args = [
        "--path",
        str(points_file),
        "--expected-dim",
        "3",
    ]
    # validate_output.main raises SystemExit on failure → capture it
    with pytest.raises(SystemExit) as excinfo:
        validate_script.main(argv=args)
    # Our validate_main should exit with 0 on success
    assert excinfo.value.code == 0

    captured = capsys.readouterr()
    assert "VALIDATION PASSED" in captured.out
