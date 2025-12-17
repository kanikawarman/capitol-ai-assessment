# tests/test_validate_output.py

"""
Tests for the Qdrant output validator.

These tests verify that `validate_output.py` correctly detects valid,
invalid, and edge-case embedding output structures.
"""


import json
import math
import sys
from pathlib import Path

import pytest

from src.capitol_pipeline.scripts.validate_output import (
    load_points,
    validate_point,
    main as validate_main,
)


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------


def make_valid_point(
    idx: int = 0,
    vector_dim: int = 4,
    nested_metadata: bool = False,
):
    """Create a minimal valid point structure for reuse in tests."""
    metadata = {
        "title": f"Doc {idx}",
        "url": f"https://example.com/{idx}",
        "external_id": f"ID{idx}",
    }

    payload = {
        "text": f"Sample text {idx}",
    }

    if nested_metadata:
        payload["metadata"] = metadata
    else:
        payload.update(metadata)

    return {
        "id": f"ID{idx}",
        "vector": [float(i) for i in range(vector_dim)],
        "payload": payload,
    }


# -------------------------------------------------------------------
# Unit tests for validate_point
# -------------------------------------------------------------------


def test_validate_point_valid_flat_metadata():
    point = make_valid_point(idx=1, vector_dim=3, nested_metadata=False)
    errors, warnings = validate_point(point, idx=0, expected_dim=3)

    assert errors == []
    # Flat metadata still inferred, but no required warnings by default
    assert warnings == []


def test_validate_point_valid_nested_metadata():
    point = make_valid_point(idx=2, vector_dim=3, nested_metadata=True)
    errors, warnings = validate_point(point, idx=0, expected_dim=3)

    assert errors == []
    assert warnings == []


def test_validate_point_missing_vector():
    point = make_valid_point()
    point.pop("vector")

    errors, warnings = validate_point(point, idx=0, expected_dim=4)

    assert any("missing 'vector'" in e for e in errors)
    # no need to assert on warnings here
    assert isinstance(warnings, list)


def test_validate_point_wrong_vector_dim():
    point = make_valid_point(vector_dim=4)
    # expected_dim doesn't match actual length
    errors, _ = validate_point(point, idx=0, expected_dim=1536)

    assert any("vector length 4 != expected_dim 1536" in e for e in errors)


def test_validate_point_non_finite_vector_value():
    point = make_valid_point()
    point["vector"][1] = math.inf  # inject a bad value

    errors, _ = validate_point(point, idx=0, expected_dim=4)

    assert any("is not a finite number" in e for e in errors)


def test_validate_point_missing_payload_text():
    point = make_valid_point()
    del point["payload"]["text"]

    errors, warnings = validate_point(point, idx=0, expected_dim=4)

    assert any("payload missing required 'text' field" in e for e in errors)
    assert isinstance(warnings, list)


def test_validate_point_empty_text_warning():
    point = make_valid_point()
    point["payload"]["text"] = "   "  # whitespace only

    errors, warnings = validate_point(point, idx=0, expected_dim=4)

    assert not errors
    assert any("payload.text is empty/whitespace" in w for w in warnings)


def test_validate_point_missing_payload():
    point = make_valid_point()
    point.pop("payload")

    errors, warnings = validate_point(point, idx=0, expected_dim=4)

    assert any("missing 'payload'" in e for e in errors)
    # Should early-return, so warnings should be empty list
    assert warnings == []


def test_validate_point_metadata_type_error():
    point = make_valid_point(nested_metadata=True)
    point["payload"]["metadata"] = "not-a-dict"

    errors, _ = validate_point(point, idx=0, expected_dim=4)

    assert any("payload.metadata exists but is not a dict" in e for e in errors)


def test_validate_point_missing_expected_meta_keys_gives_warnings():
    point = make_valid_point()
    # Remove expected metadata keys
    for key in ["title", "url", "external_id"]:
        point["payload"].pop(key, None)

    errors, warnings = validate_point(point, idx=0, expected_dim=4)

    # still valid structurally (no errors)
    assert errors == []
    # but we should get warnings for missing expected fields
    assert any("metadata missing expected field 'title'" in w for w in warnings)
    assert any("metadata missing expected field 'url'" in w for w in warnings)
    assert any("metadata missing expected field 'external_id'" in w for w in warnings)


# -------------------------------------------------------------------
# Unit tests for load_points
# -------------------------------------------------------------------


def test_load_points_array_json(tmp_path: Path):
    points = [make_valid_point(idx=0)]
    file_path = tmp_path / "points_array.json"
    file_path.write_text(json.dumps(points), encoding="utf-8")

    loaded = load_points(file_path)
    assert len(loaded) == 1
    assert loaded[0]["id"] == "ID0"


def test_load_points_jsonl(tmp_path: Path):
    points = [make_valid_point(idx=i) for i in range(2)]
    lines = "\n".join(json.dumps(p) for p in points)
    file_path = tmp_path / "points_jsonl.jsonl"
    file_path.write_text(lines, encoding="utf-8")

    loaded = load_points(file_path)
    assert len(loaded) == 2
    assert loaded[0]["id"] == "ID0"
    assert loaded[1]["id"] == "ID1"


def test_load_points_invalid_json_raises(tmp_path: Path):
    file_path = tmp_path / "bad.json"
    # Neither valid JSON array nor valid per-line JSON
    file_path.write_text("not valid json at all", encoding="utf-8")

    with pytest.raises(ValueError):
        load_points(file_path)


def test_load_points_empty_file_raises(tmp_path: Path):
    file_path = tmp_path / "empty.json"
    file_path.write_text("", encoding="utf-8")

    with pytest.raises(ValueError):
        load_points(file_path)


# -------------------------------------------------------------------
# Lightweight "integration" tests for the CLI entrypoint (main)
# -------------------------------------------------------------------


def test_validate_main_passes_on_valid_file(tmp_path: Path, capsys, monkeypatch):
    points = [make_valid_point(idx=0, vector_dim=4)]
    file_path = tmp_path / "valid_points.json"
    file_path.write_text(json.dumps(points), encoding="utf-8")

    # Simulate: python validate_output.py --path <file> --expected-dim 4
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "validate_output.py",
            "--path",
            str(file_path),
            "--expected-dim",
            "4",
        ],
    )

    # main() calls SystemExit; we assert it exits with code 0
    with pytest.raises(SystemExit) as excinfo:
        validate_main()

    assert excinfo.value.code == 0

    captured = capsys.readouterr()
    assert "VALIDATION PASSED" in captured.out


def test_validate_main_fails_on_invalid_file(tmp_path: Path, capsys, monkeypatch):
    # Missing vector entirely -> should fail
    point = make_valid_point(idx=0)
    point.pop("vector")
    file_path = tmp_path / "invalid_points.json"
    file_path.write_text(json.dumps([point]), encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "validate_output.py",
            "--path",
            str(file_path),
            "--expected-dim",
            "4",
        ],
    )

    with pytest.raises(SystemExit) as excinfo:
        validate_main()

    # Non-zero exit code on failure
    assert excinfo.value.code == 1

    captured = capsys.readouterr()
    assert "VALIDATION FAILED" in captured.out
    assert "missing 'vector'" in captured.out
