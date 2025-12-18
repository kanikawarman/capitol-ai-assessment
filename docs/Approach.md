# Approach

This document explains the engineering thought process, decisions, and trade-offs made while implementing the Capitol AI ingestion pipeline. It follows the provided checklist and aims to be explicit about reasoning so reviewers can understand priorities, constraints, and where to focus future work.

---

## 1. Problem Analysis

### Initial understanding
- Transform complex, nested customer API JSON into a standardized Qdrant-ready document format and generate vector embeddings for text search.
- Produce artifacts useful for QA and vector ingestion (transformed docs, Qdrant points with embeddings, run metadata).

### Key challenges in the customer API data
- Highly nested content organized in `content_elements` with mixed types (text, html, images, widgets).
- Multiple places for the same metadata (headlines, canonical_url, promo items), requiring fallbacks.
- Irregular taxonomy: sections/categories/tags may be deeply nested or absent.
- Non-uniform date formats, missing fields, or malformed entries.

### Complexity assessment
- The task is primarily data transformation complexity, with engineering required for reliability (error handling, idempotency) and scalability (batching embeddings).
- Embeddings add operational complexity (API calls, rate limits, cost).
- Containerization and CLI make deployment straightforward but do not add functional complexity.

---

## 2. Approach Selection

### Chosen path
- In practice, I focused on Path A to full depth (robust transformation + tests) and implemented a practical subset of Path B (Docker, CLI, logging, env-based config), rather than full infra-as-code or a deployed AP.

### Why this path
- Shows both engineering depth (transformers, cleaning, validation) and deployment skills (Docker, CLI, logging).
- Aligns with assessment expectations: transform data, produce validated outputs, and provide reproducible runs.

### Time considerations
- Prioritized core transformation and embedding correctness first; deployment and tests next; additional production features as optional improvements if time permits.

---

## 3. Thought Process

### Problem breakdown
1. Load raw JSON with schema flexibility (list or wrapped object).
2. Extract and normalize text and metadata from raw documents into `InternalDocument`.
3. Deduplicate documents by `external_id`.
4. Optionally generate embeddings in batches and build Qdrant points.
5. Save outputs with timestamped versioning and metadata.

### Prioritization
- Highest: correct text extraction & schema conformity (required for Qdrant ingestion).
- High: safe embedding pipeline (retry/backoff, truncation) to avoid API failures.
- Medium: CLI ergonomics and logging for reproducible runs.
- Lower: streaming or heavy optimization (left for future improvements).

### Iteration strategy
- Start with minimal functional pipeline (extract, map, write transformed docs).
- Add embedding layer and tests with fake embeddings to avoid API dependency during development.
- Add Docker, logging, and metadata generation.

### Development workflow
- Implement transformers with unit tests to ensure text-cleaning invariants.
- Use integration tests (end-to-end) with fake embeddings to verify overall pipeline.
- Add Dockerfile and small docs for reproducibility.

---

## 4. Technology Selection Trade-offs

### Embedding Service
Options considered: OpenAI, Sentence Transformers, Cohere.

- OpenAI (text-embedding-3-small): Chosen.
  - Pros: simple API, fast, low per-token cost, high quality for semantic search.
  - Cons: network dependency, cost at scale, rate limiting.
- Sentence Transformers (local): Good for offline/no-cost, but heavy (model download, CPU/GPU cost), slower on CPU.
- Cohere: comparable API service, similar trade-offs to OpenAI.

Trade-off rationale: Use OpenAI for assessment due to ease of integration and predictable quality; implement fake embeddings for tests and leave switching models as a future configuration.

### Vector Database
Options considered: Qdrant, Chroma, Weaviate, Pinecone.

- Decision: Produce Qdrant-compatible JSON (no live upload by default).
  - Pros: avoids coupling test infra to a running DB; output matches target format for easy ingestion.
  - Cons: doesn't exercise upload integration in this iteration.

Rationale: For an assessment, generating validated Qdrant JSON is sufficient and reduces operational surface area. A future enhancement would add a `--upload` mode that integrates with `qdrant-client` or a docker-compose setup including Qdrant.

### Processing Approach
- Synchronous batching: chosen for simplicity and deterministic ordering.
- Considered async: would improve throughput but adds complexity for error tracking and rate-limit management.
- Streaming: left for future work; current approach loads dataset into memory which is fine for the assessment-sized dataset.

### HTML Parsing
Options: BeautifulSoup, lxml, built-in `html.parser`, regex.

- Choice: Lightweight approach that relies on `html.unescape` + simple regex to strip tags for this assessment.
- Trade-offs: Regex is faster and minimal-dependency, but not as robust as BeautifulSoup for pathologic HTML. For production, prefer BeautifulSoup or lxml.

### Error Handling Depth
- Implemented robust recoverable handling (skip invalid docs, log warnings) and retries for API calls with exponential backoff.
- Trade-off: Avoided exhaustive defensive code for every rare schema variance due to time constraints; favored clear logging and maintainable fallback rules.

---

## 5. Data Transformation Decisions

### Content Elements Processing
- Strategy: Iterate `content_elements` in original order; include `text` and `html` types; ignore media-only or widget content unless textual content is discoverable.
- Order: Preserve source order and concatenate fragments with spaces (head-to-tail), assuming the most important content appears early.
- Filtering: Skip elements with empty/whitespace-only content or types known to be non-text (images, embeds) unless they contain textual captions.
- Non-text elements: Excluded from main `text` but metadata like `thumbnail_url` extracted from promo items.

### HTML Stripping
- Approach: `html.unescape()` then simple regex to remove tags and a small markdown-link regex to preserve link text.
- Trade-off: Quick and low dependencies; may not perfectly handle nested scripts/styles. For production, swapping to `BeautifulSoup` is recommended.
- Whitespace: Collapse multiple spaces and reduce long runs of newlines to two; trim leading/trailing whitespace.
- Special characters: `html.unescape` handles typical entities; unusual encodings would be logged for inspection.

### Taxonomy Flattening
- Flatten nested taxonomy arrays into simple lists for `categories`, `tags`, and `sections`.
- Prioritize fields: `taxonomy.categories` → `categories`, `taxonomy.tags` → `tags`, `sections` included as-is.
- Duplicates: Remove duplicates by value while preserving order.

### URL Management
- Prefer `canonical_url` or `url` when present.
- No automatic resolution of relative URLs in the current version (left as a future improvement) — base URL determination requires either a provided site base or metadata from the input.

### Missing Data
- Philosophy: Fail-soft for optional fields, fail-fast (skip) only for missing core content (no text) or if `external_id` is entirely absent in a way that prevents deduplication/schema mapping.
- Required field failures produce logged warnings and increment skipped counters; processing continues for other documents.
- Optional fields omitted silently and replaced with safe defaults (`[]`, `None`, `""`).

---

## 6. Architecture Decisions

### Code structure
- `loaders.py` — input loading and flexible schema handling.
- `transformers.py` — text extraction, cleaning, and metadata mapping.
- `embeddings.py` — embedding generation, backoff, and fake-embedding mode.
- `pipeline.py` — orchestration, deduplication, batching, file I/O, and metadata.
- `models.py` — Pydantic data models describing internal and output formats.
- `run_pipeline.py` — CLI entrypoint with argument parsing and logging.

### Separation of concerns
- Each module has a single responsibility; transformations are pure/isolated to make unit testing straightforward.
- Pipeline orchestrates modules and handles IO/side-effects.

### Design patterns
- Functional decomposition for transformers.
- Retry/backoff helper for embedding calls.
- Configuration via environment variables (12-factor approach).

### Modularity & reusability
- Components can be reused in different orchestration contexts (e.g., a web API or task queue).
- `embed_texts` can be replaced or monkeypatched in tests.

---

## 7. Testing Strategy

### What to test
- Unit tests for text-cleaning functions and metadata mappings.
- Embedding batching behavior (using fake embeddings).
- End-to-end pipeline with small fixtures to validate outputs and run metadata.

### Coverage goals
- Focus on correctness of transform logic (high coverage there), moderate coverage for pipeline orchestration.
- Less coverage for Dockerfile and environment permutations (manual verification suffices).

### Test data
- Small fixtures (`raw_small.json`) for unit/integration tests.
- Expectation: tests should run without external API calls by setting `USE_FAKE_EMBEDDINGS=1`.

### Trade-offs
- Avoid heavy integration tests requiring a live OpenAI key or Qdrant instance — that would slow CI and complicate runs for reviewers.

---

## 8. Performance & Operational Considerations

This section focuses on how the pipeline balances **speed, cost, robustness, and simplicity** for an assessment-scale workload, and what was intentionally left out for future iterations.

### 8.1 Optimizations Made

- **Batched embedding calls**  
  - Documents are embedded in configurable batches (`BATCH_SIZE`, default 100).  
  - This reduces API overhead, improves throughput, and keeps latency predictable even as the number of documents grows.

- **Character-level truncation before embedding**  
  - Long texts are truncated to `MAX_EMBEDDING_CHARS` (default 8000) *only for the embedding API*, while the full text is preserved in the transformed output.  
  - This keeps payloads smaller, prevents token-limit errors, and reduces OpenAI costs without changing the stored canonical text.

- **Lean in-memory processing for the assessment scale**  
  - The current implementation processes lists of documents in memory, which is perfectly adequate for the provided dataset (50 documents) and small-to-medium workloads.  
  - No unnecessary caching or on-disk intermediate artifacts are created, which keeps the code simple and easy to reason about.

### 8.2 Supporting Mechanisms That Impact Performance & Robustness

Although not “micro-optimizations,” a few design choices directly improve **operational performance** and reliability:

#### Output Validation Script

- **Purpose**: Verify that generated Qdrant points adhere to the expected schema before ingestion.
- **Location**: `src/capitol_pipeline/scripts/validate_output.py`
- **Usage**:
  ```bash
  python -m src.capitol_pipeline.scripts.validate_output \
    --qdrant-file output/qdrant_points_*.json \
    --schema data/qdrant_schema.md
  ````

* **Checks**:

  * All required fields are present
  * Field types are correct (string, array, number, etc.)
  * Embedding vectors have the expected dimension (1536)
  * Required fields are non-null

This effectively turns schema validation into a **cheap safety net** that prevents bad batches from propagating downstream.

#### Batch Processing

* The pipeline’s batching is not just about API efficiency; it also:

  * Prevents excessive memory growth on larger inputs.
  * Provides natural checkpoints for logging and progress tracking.
  * Creates a clean hook for future parallelization (e.g., multiple workers per batch).

Example configuration:

```bash
python -m src.run_pipeline --batch-size 50
```

#### Retry Logic for External Calls

* Embedding calls use **exponential backoff** for transient failures (rate limits, temporary 5xx errors):

  * Up to 5 retries with waits of `1s, 2s, 4s, 8s, 16s`.
  * Each retry is logged; permanent errors (e.g., auth issues) fail fast.

This keeps the pipeline **resilient under imperfect network conditions** without complicating the core transformation code.

#### Deduplication by `external_id`

* Documents are deduplicated using `external_id`:

  * A set of seen IDs is maintained.
  * Subsequent duplicates are skipped and logged.
* This prevents:

  * Repeated embedding of identical content
  * Redundant storage and unnecessary API spend

#### Cost Estimation

* A lightweight cost estimate is computed using:

  ```text
  tokens_per_doc ≈ char_count / 4
  cost = total_tokens × $0.02 / 1M tokens  # for text-embedding-3-small
  ```
* This is stored in `run_metadata_*.json` to give operators a feel for **per-run cost**, which is useful when scaling up.

#### Docker Composability

* The Docker image is designed to be easy to compose with other services:

  * Can be paired with a Qdrant container and a small API service via `docker-compose.yml` in the future.
  * This doesn’t directly speed up a single run, but it lowers friction for **horizontal scaling and orchestration**, which matters at higher volumes.

### 8.3 What Was *Not* Optimized (Deliberately)

* **No streaming / chunked loading yet**

  * The pipeline loads documents into memory in one go.
  * This keeps the control flow simple for the assessment; streaming would be introduced once datasets are large enough to justify the added complexity.

* **No async / concurrent embedding calls**

  * All embedding calls are synchronous batched requests.
  * Async would help at very large scale, but adds complexity around rate limiting, error handling, and observability that isn’t necessary for the current scope.

* **No persistent embedding cache**

  * There is no cross-run cache of embeddings keyed by document hash.
  * This would significantly reduce cost and runtime for re-runs, but requires decisions about storage, TTL, and invalidation that are better handled in a production phase.

### 8.4 Scalability Trade-offs

* The current architecture is ideal for **small-to-medium workloads** like the provided dataset.
* To scale to **hundreds of thousands or millions** of documents, the next steps would be:

  * Streaming or chunked JSON reading.
  * Async or multi-process embedding workers.
  * A persistent embedding cache.
  * Distributed orchestration (e.g., Airflow, Kubernetes, or a simple queue + workers model).

### 8.5 Memory vs. Speed

* The pipeline intentionally favors:

  * **Clarity and determinism** over micro-optimizations.
  * Simple in-memory lists over more complex streaming/checkpoint mechanisms.
* For very large datasets, this design would evolve toward:

  * Iterator/stream-based processing.
  * Checkpointing and resumable runs.
  * Possibly sharding work across multiple machines or containers.

---

## 9. Production Readiness

### Included production features
- Structured logging (console + file), retry/backoff on API calls, run metadata, timestamped outputs for idempotency, argument-driven configuration, Dockerfile for containerization.

### Left out
- Live Qdrant uploads, persistent caches, advanced observability (metrics export), and robust auth/secret management.

### Security considerations
- Avoid storing secrets in code; rely on environment variables for API keys.
- Dockerfile uses minimal base image; more hardening can be done for production.

### Monitoring trade-offs
- Logs and run metadata provide basic observability; Prometheus/Grafana integration is left for future work.

---

## 10. Challenges Encountered

### Technical difficulties
- Handling the many schema variants in raw documents required pragmatic fallback rules rather than exhaustive mappings.
- Deciding how much HTML parsing to do — deeper parsing added time and complexity.

### Interesting problems solved
- Built a robust truncation + batching approach that minimizes API errors while preserving most important text.
- Designed an approach where tests can run without network calls via `USE_FAKE_EMBEDDINGS`.

### Unexpected discoveries
- Many documents had empty or near-empty `content_elements`, requiring safe skips and clear logging.

---

## 11. What Would Be Done Differently

### With more time
- Implement a sentence-boundary truncation to preserve semantic completeness of embeddings.
- Add embedding caching keyed by document hash.
- Add optional live upload to Qdrant and end-to-end integration tests with a local Qdrant in docker-compose.
- Implement streaming JSON processing and an async embedding pipeline.
- Improve HTML parsing using `BeautifulSoup` or `lxml` for robustness.

### With different constraints
- Production (large scale): move to distributed workers, a message queue, persistent caches, and robust monitoring/alerts.
- Real-time needs: replace batch-oriented design with streaming ingestion and near-real-time embedding updates.

---

## 12. Known Limitations

The current implementation is intentionally scoped for the assessment, prioritizing correctness, clarity, and reliability over full production-scale capabilities. Key limitations are grouped below.

### **Functional & Data-Handling Limitations**

- **HTML parsing is intentionally lightweight**  
  Complex or malformed HTML may not be perfectly handled using the current regex-based approach. A more robust parser (BeautifulSoup, lxml) would be needed for production-grade content normalization.

- **Schema variance handling is pragmatic, not exhaustive**  
  The pipeline covers common field patterns, but unusual or deeply inconsistent customer API shapes may require additional mapping logic or validators.

- **Integration tests avoid live external services**  
  Tests use fake embeddings by default and do not exercise real OpenAI/Qdrant integrations. A production pipeline would require dedicated integration/E2E environments.

- **Security and runtime hardening not implemented**  
  API keys rely on environment variables; no vault/secret manager integration or container hardening is included in this assessment version.

---

### **Performance & Scalability Limitations**

1. **Text Truncation**
   - Embedding inputs are truncated to 8,000 characters to prevent token-limit errors.  
   - Long articles lose trailing content in embeddings (though full text is preserved in transformed outputs).  
   - Future: sentence-aware truncation, intelligent chunking, or sliding-window embeddings.

2. **No Streaming or Chunked Loading**
   - The pipeline loads the entire dataset into memory at once.  
   - Works for tens of thousands of documents, but not for multi-GB datasets.  
   - Future: streaming JSON parsing, generator-based pipelines, or chunkwise processing.

3. **File-Based Vector DB Integration Only**
   - Outputs Qdrant-ready JSON but does not upload to a running Qdrant instance.  
   - Chosen to keep the assessment self-contained and execution environment-neutral.  
   - Future: optional `--upload` mode using `qdrant-client` and collection management.

4. **No Incremental / Resumable Processing**
   - Runs are all-or-nothing; restarting requires reprocessing everything.  
   - Future: checkpointing, processed-ID tracking, and resumable execution.

5. **Single Embedding Model**
   - Only `text-embedding-3-small` is supported.  
   - Future: configurable model selection, offline models, multilingual handling, and quality/cost trade-off tuning.

6. **No Cross-Run Caching**
   - Identical documents are re-embedded on each run, increasing cost and runtime for repeated jobs.  
   - Future: embed-once caching keyed by document hash, with TTL or invalidation strategy.

7. **Single-Threaded Embedding Flow**
   - Embeddings are computed synchronously in batches.  
   - Adequate for the assessment dataset, but suboptimal for large-scale ingestion or near-real-time use cases.  
   - Future: async embedding workers, multiprocessing, or distributed task queues.

These limitations were conscious trade-offs to prioritize clarity, maintainability, and correctness within assessment scope. All of them have clear upgrade paths for a production environment.


---

## 13. Areas for Improvement

- Replace regex HTML stripping with `BeautifulSoup` for correctness.
- Add persistent embedding cache (redis or file store).
- Add `--upload` mode to push points directly to Qdrant.
- Add async workers and streaming input support.
- Add Prometheus metrics and alerting for failures and throughput.

---

## 14. Lessons Learned

- Start with strong data contracts and unit tests for transformation — this yields fast iteration and confidence.
- Make external API interactions pluggable and mockable to keep tests fast and deterministic.
- Small datasets benefit more from simplicity and determinism than premature optimization.

---

### Closing notes
This `Approach.md` intends to make the engineering rationale fully transparent. If you'd like, I can:
- Add explicit code pointers (line numbers) to where each decision is implemented,
- Add sample outputs for more examples,
- Or convert this into slides or a shorter executive summary for non-technical reviewers.

