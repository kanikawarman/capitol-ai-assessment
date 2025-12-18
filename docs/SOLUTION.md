# Solution.md

## 1) Field Mapping (raw → Qdrant payload)

| Qdrant Field | Source (raw JSON) | Notes / Fallbacks |
|---|---|---|
| `external_id` | `_id` or `id` | Primary stable id; used for dedupe
| `title` | `headlines.basic` → `title` | Prefer `headlines.basic`
| `url` | `canonical_url` → `url` | Canonical URL when present
| `published_at` | `publish_date` → `created_date` | ISO-8601 when possible
| `text` | Concatenated `content_elements` (text/html) | HTML entities unescaped, tags stripped
| `categories` | `taxonomy.categories[].name` | Flattened list
| `tags` | `taxonomy.tags[].text` | Flattened list
| `sections` | `taxonomy.sections` | Preserved array
| `thumbnail_url` | `promo_items.*.url` (first) | Extract promo image if available
| `original` | full raw document | Stored for debugging/audit

> Qdrant point structure: `{ id: external_id, vector: [...], payload: { text, title, url, published_at, categories, tags, sections, thumbnail_url, original } }`

---

## 2) Transformation Pipeline (overview)

1. Load input JSON (support list or `{documents|results}` wrapper)
2. For each raw doc:
   - Extract `external_id`, `title`, `url`, `published_at` using fallbacks
   - Build `text` by iterating `content_elements` in source order, collecting `text`/`html` fragments
   - Clean fragments: `html.unescape` → strip tags → collapse whitespace → fix markdown links
   - Create `InternalDocument` with metadata and `original`
3. Deduplicate by `external_id` (keep first)
4. If `skip_embeddings` is False:
   - Truncate text to `MAX_EMBEDDING_CHARS` (default 8000) for embedding input
   - Batch texts (configurable `BATCH_SIZE`) and call embedding API with retry/backoff
   - Combine embeddings with payloads to form Qdrant points
5. Write outputs (unless `dry_run`):
   - `transformed_TIMESTAMP.json` (transformed docs)
   - `qdrant_points_TIMESTAMP.json` (points with vectors)
   - `run_metadata_TIMESTAMP.json` (summary, cost estimate)

---

## 3) Edge Cases Handled

- [x] Missing `external_id` → warn / skip or assign generated id when safe
- [x] Empty or missing `content_elements` → skip document (logged)
- [x] Duplicate `external_id` → keep first, log duplicates
- [x] Malformed or missing dates → attempt parse, else null + warn
- [x] HTML entities & tags → unescape & strip
- [x] Markdown links → preserve link text, remove URL
- [x] Oversized text for embeddings → truncate to `MAX_EMBEDDING_CHARS` (keep full text in output)
- [x] Embedding API rate limits / transient errors → exponential backoff retries
- [x] Tests: fake-embedding mode to avoid external API calls in CI

---

## 4) Configuration Summary (env vars + CLI args)

Environment variables

| Name | Purpose | Default |
|---|---:|---|
| `OPENAI_API_KEY` | OpenAI API key for embeddings | (required for live embeddings)
| `USE_FAKE_EMBEDDINGS` | Use fake vectors for tests (`1` = true) | `0`
| `MAX_EMBEDDING_CHARS` | Max chars sent to embedding model | `8000`
| `BATCH_SIZE` | Documents per embedding batch | `100`

CLI Arguments (exposed via `python -m src.run_pipeline`)

| Arg | Purpose | Default |
|---|---:|---|
| `--input` | Path to raw JSON | `data/raw_customer_api.json` |
| `--output-dir` | Directory for outputs | `output` |
| `--limit` | Process only first N docs | `None` (all) |
| `--dry-run` | Do everything but write files | `False` |
| `--skip-embeddings` | Produce transformed docs only | `False` |
| `--batch-size` | Batch size for embeddings | `100` |
| `--no-history` | Overwrite instead of timestamped files | `False` |

---

Notes: defaults reflect the repository implementation. Use `USE_FAKE_EMBEDDINGS=1` for fast, offline tests. `--dry-run` performs transform/dedupe but skips all file writes.

