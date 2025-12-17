"""Output Validation Script

Validates that generated Qdrant points JSON conforms to schema requirements:
  - Required fields present and correctly typed (id, vector, payload)
  - Vector dimensionality matches expected size
  - Payload contains required and expected metadata fields
  - Text content is non-empty and valid

Usage:
    python -m src.capitol_pipeline.scripts.validate_output \\
        --path output/qdrant_points.json \\
        --expected-dim 1536

Exits with code 0 on success, 1 on validation failure, 2 on argument error.
"""

#!/usr/bin/env python
import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional


def load_points(path: Path) -> List[Dict[str, Any]]:
    """Load Qdrant points from a JSON file.

    Supports:
      - a JSON array of objects
      - newline-delimited JSON (JSONL)
    """
    with path.open("r", encoding="utf-8") as f:
        content = f.read().strip()

    # Try: full file is a single JSON array
    try:
        data = json.loads(content)
        if isinstance(data, list):
            return data
        else:
            raise ValueError("Top-level JSON is not a list of points.")
    except json.JSONDecodeError:
        pass  # fall through to JSONL

    # Try: JSON Lines (one JSON object per line)
    points: List[Dict[str, Any]] = []
    for line_no, line in enumerate(content.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Failed to parse JSON on line {line_no}: {e}"
            ) from e
        if not isinstance(obj, dict):
            raise ValueError(
                f"Line {line_no} JSON is not an object (got {type(obj)})"
            )
        points.append(obj)

    if not points:
        raise ValueError("No points found in file.")

    return points


def is_finite_number(x: Any) -> bool:
    """Check if value is a finite number (int or float).
    
    Args:
        x: Value to check
        
    Returns:
        True if x is a numeric type with a finite value, False otherwise
    """
    return isinstance(x, (int, float)) and math.isfinite(x)


def validate_point(
    point: Dict[str, Any],
    idx: int,
    expected_dim: Optional[int],
) -> Tuple[List[str], List[str]]:
    """Validate a single Qdrant point.

    Returns:
        (errors, warnings)
    """
    errors: List[str] = []
    warnings: List[str] = []

    # --- id ---
    pid = point.get("id")
    if pid is None:
        errors.append(f"[idx={idx}] missing 'id'")
    elif not isinstance(pid, (str, int)):
        errors.append(
            f"[idx={idx}] 'id' should be str or int, got {type(pid).__name__}"
        )

    # --- vector ---
    vector = point.get("vector")
    if vector is None:
        errors.append(f"[idx={idx}] missing 'vector'")
    elif not isinstance(vector, list):
        errors.append(
            f"[idx={idx}] 'vector' should be a list, got {type(vector).__name__}"
        )
    else:
        if expected_dim is not None and len(vector) != expected_dim:
            errors.append(
                f"[idx={idx}] vector length {len(vector)} != expected_dim {expected_dim}"
            )
        # basic numeric sanity
        for j, v in enumerate(vector):
            if not is_finite_number(v):
                errors.append(
                    f"[idx={idx}] vector[{j}] is not a finite number (got {repr(v)})"
                )
                break  # no need to spam too much

    # --- payload ---
    payload = point.get("payload")
    if payload is None:
        errors.append(f"[idx={idx}] missing 'payload'")
        return errors, warnings
    if not isinstance(payload, dict):
        errors.append(
            f"[idx={idx}] 'payload' should be an object, got {type(payload).__name__}"
        )
        return errors, warnings

    # text
    text = payload.get("text")
    if text is None:
        errors.append(f"[idx={idx}] payload missing required 'text' field")
    elif not isinstance(text, str):
        errors.append(
            f"[idx={idx}] payload.text should be a string, got {type(text).__name__}"
        )
    elif not text.strip():
        warnings.append(f"[idx={idx}] payload.text is empty/whitespace")

    # --- metadata: nested OR flat ---
    # 1) Preferred: payload["metadata"] if present and dict
    metadata: Optional[Dict[str, Any]] = None
    if "metadata" in payload:
        if isinstance(payload["metadata"], dict):
            metadata = payload["metadata"]
        else:
            errors.append(
                f"[idx={idx}] payload.metadata exists but is not a dict "
                f"(got {type(payload['metadata']).__name__})"
            )
    else:
        # 2) Your current schema: metadata is flattened at payload level
        #    We infer it as "all keys except 'text'".
        flat_meta = {
            k: v for k, v in payload.items() if k not in {"text", "metadata"}
        }
        metadata = flat_meta

    if metadata is None:
        errors.append(f"[idx={idx}] could not determine metadata dict")
    else:
        # Key fields we *expect* but treat as WARNINGS if missing:
        expected_meta_keys = ["title", "url", "external_id"]
        for key in expected_meta_keys:
            if key not in metadata:
                # could be legitimately missing -> warning only
                warnings.append(
                    f"[idx={idx}] metadata missing expected field '{key}'"
                )

        # Optional: you can add light type checks without being too strict
        url = metadata.get("url")
        if url is not None and not isinstance(url, str):
            warnings.append(
                f"[idx={idx}] metadata.url is not a string (got {type(url).__name__})"
            )

    return errors, warnings

def main(argv: list[str] | None = None) -> None:
    """Validate Qdrant points output file.
    
    Loads a JSON file of Qdrant points and validates:
      - All required fields present and correctly typed
      - Vector dimensionality matches expected size
      - Payload structure is valid
      - Text content is present and non-empty
    
    Args:
        argv: Command-line arguments. If None, uses sys.argv[1:]
        
    Raises:
        SystemExit: With code 0 on success, 1 on validation failure
    """
    parser = argparse.ArgumentParser(
        description="Validate Qdrant points JSON output."
    )
    parser.add_argument(
        "--path",
        type=str,
        required=True,
        help="Path to qdrant_points_with_embeddings.json",
    )
    parser.add_argument(
        "--expected-dim",
        type=int,
        default=None,
        help="Expected vector dimensionality (e.g. 1536). "
             "If not provided, dimensionality is not enforced.",
    )
    args = parser.parse_args(argv)

    path = Path(args.path)

    try:
        points = load_points(path)
    except Exception as e:
        print(f"FAILED TO LOAD FILE: {e}")
        raise SystemExit(1)

    total = len(points)
    all_errors: List[str] = []
    all_warnings: List[str] = []

    for idx, point in enumerate(points):
        errors, warnings = validate_point(point, idx, args.expected_dim)
        all_errors.extend(errors)
        all_warnings.extend(warnings)

    if all_errors:
        print("VALIDATION FAILED:\n")
        for err in all_errors:
            print(err)
        print(f"\nTotal errors: {len(all_errors)}")
        if all_warnings:
            print(f"Total warnings: {len(all_warnings)}")
        raise SystemExit(1)
   
    # Success path
    print("VALIDATION PASSED")
    print(f"Total points: {total}")
    if all_warnings:
        print("\nWarnings (non-fatal):")
        for w in all_warnings:
            print(w)
        print(f"\nTotal warnings: {len(all_warnings)}")

    # Explicit success exit code so tests can assert on it
    raise SystemExit(0)

if __name__ == "__main__":
    main()

