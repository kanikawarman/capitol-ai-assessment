# Testing Overview

This document summarizes the testing strategy, how to run the test suite, and what each category of tests covers. The goal is to ensure correctness, robustness, and confidence in the pipeline’s transformation and embedding behavior. This aligns with the evaluation categories **Correctness & Robustness** and **Code Quality**.

## Purpose

- Verify the correctness of transformation logic (text extraction, metadata mapping, taxonomy flattening).
- Confirm reliable embedding behavior using both fake embeddings and real API calls.
- Validate that the full pipeline behaves predictably for small datasets.
- Ensure schema compliance of generated Qdrant payloads.

## Test Types Included

- Unit tests
  - Target: `transformers.py`, `models.py`, helper functions.
  - Validate text cleaning, entity unescaping, tag stripping, markdown link handling.
  - Deterministic and isolated; no external dependencies.

- Embedding tests
  -  Use `USE_FAKE_EMBEDDINGS=1` to avoid network calls.
  - Validate:
    - Batch construction
    - Truncation behavior (`MAX_EMBEDDING_CHARS`)
    - Correct attachment of vectors to payloads
  - Fake embeddings ensure fast, reproducible results..

- Integration tests
  - Run the entire pipeline using a small fixture dataset (`tests/fixtures/raw_small.json`, 3 docs).
  - Covers: load → transform → dedupe → fake embed → build Qdrant points → validate outputs.
  - Ensures the pipeline works end-to-end without external services..

- Validation tests
  - Use `scripts/validate_output.py` to assert schema correctness:
    - Required fields present
    - Vector dimensions correct
    - Payload formatting matches Qdrant expectations

## How to Run Tests Locally

Basic run (from project root):

```bash
# Fast tests without calling real embedding APIs
USE_FAKE_EMBEDDINGS=1 pytest -q

# Full test run (requires OPENAI_API_KEY for real embedding tests)
pytest -q
```

Run a single test file or module:

```bash
pytest tests/test_transformers.py -q
```

Notes:
- Set `USE_FAKE_EMBEDDINGS=1` for CI or local runs where OpenAI access is not available.
- Tests are designed to be deterministic when fake embeddings are used.

## What Tests Cover (high-level)

- Text cleaning and normalization (HTML entities, tag stripping, whitespace normalization).
- Metadata extraction and fallback logic (title, URL, published date, taxonomy fields).
- Deduplication by `external_id`.
- Embedding batching and truncation logic (via fake embeddings in tests).
- Output format validation against the expected Qdrant schema.

## Quick Troubleshooting

- Failures in transformer tests: inspect `tests/test_transformers.py` to see expected inputs and outputs; run the single test with `-k` to focus.
- Embedding-related failures: ensure `USE_FAKE_EMBEDDINGS=1` is set for offline runs; for live tests, confirm `OPENAI_API_KEY` is valid and network is available.
- Output validation failures: open the generated `output/*.json` and compare fields with `data/qdrant_schema.md`.

## CI Notes

- CI should run `USE_FAKE_EMBEDDINGS=1 pytest -q` to avoid external API dependency and to keep runs fast and reliable.
- If a pipeline integration test requiring real embeddings is desired in CI, run it in a separate job with `OPENAI_API_KEY` available and guard costs.

## Summary

The test-suite focuses on correctness of transformations and safe, repeatable verification of embedding-related logic using a fake-embeddings mode. Tests are fast with the fake mode and suitable for running on CI.
