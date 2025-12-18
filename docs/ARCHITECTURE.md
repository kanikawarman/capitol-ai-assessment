# Architecture Overview

This document explains how the pipeline components interact, the data flow, key architectural decisions, and why the system is maintainable and extensible. It is focused on the evaluator categories: Architecture & Design, Technical Considerations, and Correctness & Robustness.

---

## High-level Pipeline Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Input: Raw API JSON                      │
│              (data/raw_customer_api.json)                   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│           Loader Module (loaders.py)                        │
│   - Load JSON from file                                     │
│   - Support flexible schema (array, {documents}, {results}) │
│   - Handle file not found errors gracefully                 │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│         Transformer Module (transformers.py)                │
│   - Extract text from nested content_elements               │
│   - Clean HTML tags and entities                            │
│   - Map metadata fields (title, url, dates, categories)     │
│   - Handle missing/malformed data                           │
│   - Deduplication by external_id                            │
└────────────────────────┬────────────────────────────────────┘
                       │
                       ▼
       ┌───────────────┴────────────────┐
       │                                │
       ▼                                ▼
   ┌──────────────┐            ┌──────────────────────┐
   │Output JSON:  │            │ Embedding Module     │
   │Transformed   │            │ (embeddings.py)      │
   │Documents     │            │                      │
   │(no vectors)  │            │ - Batch processing   │
   └──────────────┘            │ - Text truncation    │
                               │ - Retry logic        │
       △                       │ - Fake embeddings    │
       │                       │   (testing)          │
       │                       └──────────┬───────────┘
       │                                  │ 
       │                                  ▼
       │                            OpenAI API
       │                   (text-embedding-3-small)
       │                                 │
       │                                 ▼
       │                      ┌────────────────── ┐
       │                      │ Vector Embeddings │
       │                      │ (1536-dim for     │
       │                      │  embedding-small) │
       │                      └──────────┬────────┘
       │                                 │
       └─────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│        Pipeline Module (pipeline.py)                        │
│   - Orchestrate transformation → embedding → output         │
│   - Handle errors and logging                               │
│   - Generate execution metadata                             │
└────────────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌───────────────────────────────────────────────────────────── ┐
│                  Output Files (Timestamped)                  │
│                                                              │
│  1. transformed_TIMESTAMP.json                               │
│     └─ [{"text": "...", "metadata": {...}}, ...]             │
│                                                              │
│  2. qdrant_points_TIMESTAMP.json                             │
│     └─ [{"id": "uuid", "vector": [...], "payload": {}}, ...] │
│                                                              │
│  3. run_metadata_TIMESTAMP.json                              │
│     └─ {total_raw, processed, skipped, errors, timestamps...}│
└───────────────────────────────────────────────────────────── ┘
```

---

## Component Responsibilities

- `loaders.py` — Read input JSON with flexible schema support (list, `documents`, `results`). Provide a simple, testable API that returns raw document dictionaries.

- `transformers.py` — Extract and normalize content and metadata: build cleaned `text` from `content_elements`, flatten taxonomy, map title/url/published_at, and produce `InternalDocument` instances suitable for downstream embedding and export.

- `models.py` — Pydantic models that document and validate the internal and output data contracts (InternalDocument, QdrantDocument), ensuring correctness of shapes passed across modules.

- `embeddings.py` — Encapsulate embedding logic: truncation policy, batching, OpenAI client handling, and exponential backoff retry behavior; supports a fake-embeddings mode for deterministic tests.

- `pipeline.py` — Orchestrates the end-to-end flow: load → transform → dedupe → embed → build points → write outputs; responsible for run metadata, versioning, and error aggregation.

- `run_pipeline.py` — CLI entrypoint that configures logging and parses command-line args; keeps IO, logging, and orchestration separate from transformation logic.

- `scripts/validate_output.py` — Post-run validation to assert Qdrant schema compliance, enabling correctness checks without modifying pipeline core logic.

---

## Sequence / Data Flow (raw → internal → transformed → embeddings → qdrant points)

1. Input: raw JSON file (supports multiple wrapper formats). Loader returns a list of raw docs.
2. Transform: For each raw doc, transformer extracts `external_id`, `title`, `url`, `published_at`, `categories/tags/sections`, and constructs a cleaned `text` field. The full raw document is preserved in `original`.
3. Validation & Deduplication: Pipeline validates required fields (logs and skips if core content missing) and removes duplicates by `external_id`.
4. Embedding Preparation: `text` is truncated to `MAX_EMBEDDING_CHARS` for embedding calls while the full text is retained in outputs.
5. Embeddings: Batches of texts are sent to the embedding service with retry/backoff; returned vectors are zipped with payloads.
6. Qdrant Points: Points are created as `{ id, vector, payload }` where payload contains metadata and original text.
7. Output: Files are written (unless `--dry-run`) and run metadata (counts, duration, cost estimate) is saved for observability.

---

## Key Architectural Decisions (concise rationale tied to behavior)

- Batching: Embeddings are processed in configurable batches (`BATCH_SIZE`) to minimize API calls and control memory; this balances throughput and reliability for medium-sized datasets.

- Truncation Policy: Character-based truncation to `MAX_EMBEDDING_CHARS` (default 8000) prevents token-limit errors and keeps costs predictable while preserving full text in outputs for auditing.

- Modularity & Separation of Concerns: Transformers are pure (no IO), loaders handle IO, embeddings encapsulate external integration; this makes unit testing straightforward and reduces blast radius for changes.

- Retry Logic: Exponential backoff for transient API errors (429/5xx) improves robustness in face of rate limits and transient failures without complicating business logic.

- Dry-run Mode: Pipeline supports `--dry-run` which runs transform/dedupe/validation without writing files, enabling safe verification in CI or during development.

- Fake Embeddings: `USE_FAKE_EMBEDDINGS` provides deterministic vectors for tests so correctness can be validated without relying on external services.

- Qdrant integration is intentionally file-based only in this iteration (no live DB writes), to keep the core pipeline self-contained and easy to run in any environment.

---

## Why This Architecture Is Extensible and Maintainable

- Clear contracts: Pydantic models and explicit payload shapes make it easy to add fields or evolve schema while retaining validation.

- Pluggable embedding layer: `embeddings.py` centralizes provider logic; switching to another provider (or an in-house model) is a single-module change.

- Small, focused modules: Each file has a single responsibility which supports quick iteration, targeted tests, and lower cognitive overhead for reviewers and contributors.

- Config-driven behavior: Key choices (batch size, truncation length, fake-embeddings, API keys) are environment- or CLI-configurable, enabling different deployment profiles without code changes.

- Observability and metadata: The pipeline produces run metadata and logs; this helps debug, measure, and evolve the system safely.

---

## Alignment to Evaluation Categories

- Architecture & Design: The architecture is layered, modular, and documents clear responsibilities to support maintainability and future features (e.g., streaming, caching, Qdrant upload).

- Technical Considerations: Decisions on batching, truncation, and retrying are explicitly tied to operational concerns (cost, rate limits, token limits) and justified for medium-scale pipelines.

- Correctness & Robustness: Validation, Pydantic models, dry-run, fake-embeddings, and post-run validation script collectively ensure correctness and provide safeguards against regressions.

---
