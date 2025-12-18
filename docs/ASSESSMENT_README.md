# Capitol AI Assessment - Comprehensive Documentation

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [Python Version & System Requirements](#python-version--system-requirements)
3. [Installation Instructions](#installation-instructions)
4. [Configuration](#configuration)
5. [How to Run](#how-to-run)
6. [How to Verify](#how-to-verify)
7. [Architecture Overview](#architecture-overview)
8. [Key Design Decisions](#key-design-decisions)
9. [Core Components Coverage](#core-components-coverage)
10. [Path-Specific Documentation](#path-specific-documentation)
11. [Testing](#testing)
12. [Extra Implementations](#extra-implementations)
13. [Future Improvements](#future-improvements)

---

## Problem Statement

### Solution Approach

This assessment demonstrates a **full-stack, production-grade data ingestion pipeline** for Capitol AI's content management system. The solution focuses on:

1. **Robust Data Transformation**: Converting deeply nested customer API responses into standardized Qdrant-compatible document format
2. **Infrastructure & Deployment**: Containerized deployment with Docker, comprehensive logging, and error handling
3. **Data Quality**: Validation, deduplication, and comprehensive test coverage

### What Was Accomplished

- Transform customer API data (JSON) into Qdrant schema format
- Extract and clean text from nested content elements
- Generate vector embeddings using OpenAI's embedding API
- Build production-grade CLI with argument parsing and logging
- Containerize with Docker for reproducible deployments
- Comprehensive test suite covering transformation, embeddings, and validation
- Output file versioning for idempotent processing
- Structured error handling with informative logging

---

## Python Version & System Requirements

### Python Version

- **Required**: Python 3.11+
- **Tested on**: Python 3.11.x
- **Reason**: Uses modern type hints (`|` union syntax), `tomllib` standard library features, and Pydantic v2

### System Requirements

| Requirement | Details |
|---|---|
| **Operating System** | macOS, Linux, or Windows (via WSL) |
| **RAM** | Minimum 2GB (recommended 4GB+) |
| **Disk Space** | ~500MB for dependencies and output |
| **Docker** | Required for containerized deployment (optional for local runs) |
| **Network** | Required for OpenAI API calls (unless using fake embeddings) |

### Required API Keys

- **OpenAI API Key**: For text-embedding-3-small embeddings
  - Set via `OPENAI_API_KEY` environment variable
  - Obtain from [OpenAI Platform](https://platform.openai.com/api-keys)
  - Costs: ~$0.02 per 1M tokens for text-embedding-3-small

### Additional Environment Variables

```bash
# Optional: Skip actual API calls in tests
USE_FAKE_EMBEDDINGS=1

# Optional: Control embedding text truncation
MAX_EMBEDDING_CHARS=8000

# Optional: Control batch size for embedding generation
BATCH_SIZE=100

# Required for Docker deployments
OPENAI_API_KEY=<your-api-key>
```

---

## Installation Instructions

### 1. Clone Repository

```bash
git clone <repository-url>
cd capitol-ai-assessment
```

### 2. Virtual Environment Setup

#### Using Python venv

```bash
# Create virtual environment
python3.11 -m venv venv

# Activate it
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate  # Windows
```

#### Using Conda (Alternative)

```bash
conda create -n capitol-ai python=3.11
conda activate capitol-ai
```

### 3. Install Dependencies

```bash
# Install from requirements.txt
pip install -r requirements.txt

```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Required
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx

# Optional (with defaults)
USE_FAKE_EMBEDDINGS=0
MAX_EMBEDDING_CHARS=8000
```

Then load it:

```bash
# On macOS/Linux
export $(cat .env | xargs)

# Or in Python code, use python-dotenv
pip install python-dotenv
```

### 5. Docker Setup (Optional)

Install Docker Desktop from [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop).

Verify installation:

```bash
docker --version  # Should return Docker version
```

---

## Configuration

### Environment Variables

All configuration is managed through environment variables for 12-factor app compliance:

| Variable | Type | Default | Purpose |
|---|---|---|---|
| `OPENAI_API_KEY` | String | None | OpenAI API authentication token |
| `USE_FAKE_EMBEDDINGS` | Boolean (0/1) | 0 | Use mock embeddings (testing) |
| `MAX_EMBEDDING_CHARS` | Integer | 8000 | Max characters sent to embedding API |
| `BATCH_SIZE` | Integer | 100 | Documents per embedding batch |

### Configuration Priority

1. Environment variables (highest priority)
2. `.env` file
3. Hardcoded defaults (lowest priority)

### Template Configuration Files

No configuration files needed for basic operation. All settings are environment-driven.

---

## How to Run

### Local Execution (Python)

#### Basic Pipeline Execution

```bash
# With default arguments
python -m src.run_pipeline

# Limit to first N documents
python -m src.run_pipeline --limit 5

# Skip embedding generation (faster, test-only)
python -m src.run_pipeline --skip-embeddings

# Dry-run (no Qdrant upload, only file output)
python -m src.run_pipeline --dry-run

# Custom batch size for embeddings
python -m src.run_pipeline --batch-size 50

# Overwrite output files instead of versioning
python -m src.run_pipeline --no-history

# Full example with all options
python -m src.run_pipeline \
  --input data/raw_customer_api.json \
  --output-dir output \
  --limit 10 \
  --batch-size 50 \
  --dry-run \
  --skip-embeddings \
  --no-history
```

#### Check Help

```bash
python -m src.run_pipeline --help
```

### Docker Execution

#### Build Image

```bash
# Build from Dockerfile
docker build -t capitol-pipeline:latest .

# Build with custom tag
docker build -t capitol-pipeline:v1.0 .
```

#### Run Container

```bash
# Basic run with skip-embeddings
docker run --rm \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  capitol-pipeline:latest \
  --skip-embeddings

# Mount output directory for persistence
docker run --rm \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -v $(pwd)/output:/app/output \
  capitol-pipeline:latest \
  --batch-size 50

# Full options
docker run --rm \
  --name capitol-run \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -e USE_FAKE_EMBEDDINGS=1 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/output:/app/output \
  capitol-pipeline:latest \
  --input data/raw_sample.json --limit 5 --dry-run
```

#### Run Tests in Container

```bash
# Run full test suite
docker run --rm \
  --entrypoint pytest \
  capitol-pipeline:latest \
  -q

# Run specific test file
docker run --rm \
  --entrypoint pytest \
  capitol-pipeline:latest \
  tests/test_transformers.py -v

```

### Expected Execution Time

| Scenario | Time |
|---|---|
| Transform only (10 docs, skip embeddings) | 0.3-0.7 seconds |
| With embeddings (10 docs, batch size 100) | 0.4-0.9 seconds |
| Full pipeline (50 docs) | 1.5-2 seconds |
| Fake embeddings mode (50 docs) | 1.5-2 seconds |

---

## How to Verify

### 1. Validate Output Files

#### Check Output Directory Structure

```bash
ls -lh output/
# Expected files:
# - transformed_TIMESTAMP.json      (cleaned documents)
# - qdrant_points_TIMESTAMP.json    (with embeddings)
# - run_metadata_TIMESTAMP.json     (execution summary)
```

#### Verify Qdrant Schema Compliance

After running the pipeline, you can validate the generated Qdrant points file
to ensure it conforms to the expected schema.

> **Note:** You must pass the *specific* output file path.  

Example:

```bash
python -m src.capitol_pipeline.scripts.validate_output \
  --path output/qdrant_points_20251217_093733.json \
  --expected-dim 1536
```

### 2. Run Automated Tests

The embedding tests rely on the real `embed_texts` logic and use `monkeypatch`
to inject a fake client. For this reason, the `USE_FAKE_EMBEDDINGS` shortcut
**must be disabled** when running tests.

> If `USE_FAKE_EMBEDDINGS=1` is set in your shell, several tests in
> `tests/test_embeddings.py` will fail because `embed_texts` short-circuits and
> never calls the patched client.

#### Unit Tests

```bash
# Run all tests
# Make sure fake embeddings are disabled for tests

unset USE_FAKE_EMBEDDINGS  # or: export USE_FAKE_EMBEDDINGS=0
pytest -v


# Run specific test module
pytest tests/test_transformers.py -v

```

#### Integration Tests

```bash
# Test full pipeline end-to-end
pytest tests/test_pipeline_integration.py -v

# Test with fake embeddings (no API calls)
USE_FAKE_EMBEDDINGS=1 pytest tests/test_pipeline_integration.py -v
```

#### Data Quality Tests

```bash
# Test output validation
pytest tests/test_validate_output.py -v

# Verify all required fields are present
pytest tests/test_pipeline_with_validation.py -v
```

### 3. Log Analysis

#### Check Execution Logs

```bash
# View latest run logs
tail -100 logs/pipeline.log

# Filter for errors
grep ERROR logs/pipeline.log

# Get summary statistics
grep "processed:" logs/pipeline.log | tail -1
```

#### Log Levels

```bash
DEBUG:   Detailed diagnostic info (file operations, API calls)
INFO:    User-facing progress updates (documents processed, files written)
WARNING: Recoverable issues (missing fields, formatting issues)
ERROR:   Failures that halt processing
```

---

## Architecture Overview

This implementation uses a modular pipeline:

- `loaders.py` → input JSON loading and schema normalization  
- `transformers.py` → text extraction, HTML cleaning, metadata mapping  
- `embeddings.py` → truncation, batching, OpenAI integration  
- `pipeline.py` → orchestration, dedupe, file output, run metadata  

For the full architecture diagrams, component responsibilities, and data-flow details, see:
- `docs/ARCHITECTURE.md`
- `docs/SOLUTION.md` — one-page solution summary (field mapping, pipeline overview, edge cases, configuration).


---

## Key Design Decisions

- OpenAI `text-embedding-3-small` for embeddings (cost vs. quality).
- Character-based truncation (`MAX_EMBEDDING_CHARS`, default 8000).
- Batch processing (`BATCH_SIZE`, default 100).
- Deduplication by `external_id`.
- Timestamped outputs for idempotency.

Full rationale and alternatives considered are documented in:
- `docs/APPROACH.md`

---
## Core Components Coverage

The solution covers:

- Data transformation (raw CMS JSON → cleaned internal doc → Qdrant payload)
- Text handling (HTML/markdown cleanup, taxonomy flattening)
- Embeddings (batching, truncation, retry)
- Metadata mapping & deduplication

For the precise field mapping and transformation pipeline pseudocode, see:
- `docs/SOLUTION.md`
- `docs/ARCHITECTURE.md`

---

## Path-Specific Documentation

### Path A: Data Engineering Depth

**This implementation includes**:

 **Comprehensive Transformation Logic**
- All 50 documents from `raw_customer_api.json` can be processed
- Flexible HTML/markdown cleaning
- Metadata field mapping with fallbacks
- Deduplication by external_id

 **Error Handling & Validation**
- Missing field detection and logging
- Graceful skip of malformed documents
- Output validation against Qdrant schema
- Error summary in metadata output

 **Test Coverage**
- Unit tests: `test_transformers.py` (text cleaning, metadata extraction)
- Integration tests: `test_pipeline_integration.py` (end-to-end)
- Validation tests: `test_validate_output.py` (schema compliance)
- Mock embeddings for fast, API-free testing

 **Data Quality**
- Character-level truncation for embeddings
- Deduplication by ID
- Field presence validation
- Document count tracking

 **Idempotent Processing**
- Timestamped output files
- Optional history overwrite
- Safe to re-run without side effects

### Path B: Infrastructure & Deployment

**This implementation includes**:

 **Containerization**
- Multi-layer Dockerfile with:
  - Minimal base image (`python:3.11-slim`)
  - Cached dependencies layer
  - Working directory setup
  - Proper environment variables
- Docker ignore file to reduce image size
- Entrypoint/CMD for CLI argument forwarding

 **Structured Logging**
- Dual output: console (INFO) + file (DEBUG)
- Structured format: `timestamp | level | module | message`
- Log file in `logs/` directory for troubleshooting

 **CLI & Argument Parsing**
- 6 command-line arguments:
  - `--input`: Custom input file path
  - `--output-dir`: Output directory
  - `--limit`: Process N documents only
  - `--dry-run`: Skip actual uploads
  - `--skip-embeddings`: Faster mode
  - `--batch-size`: Embedding batch size
  - `--no-history`: Overwrite previous outputs

 **Environment-Driven Configuration**
- 12-factor app: All config via env vars
- No hardcoded secrets
- Support for `.env` files
- Easy to integrate with CI/CD

 **Metrics & Observability**
- Execution metadata in JSON:
  - Document counts (raw, processed, skipped)
  - Timestamps (start, end, elapsed)
  - Error count and details
  - Embedding model and dimension
  - Estimated API cost
- Log-based telemetry
- Error tracking for debugging

 **Docker Deployment**
- Clean, minimal image (< 200MB)
- Volume mounts for data persistence
- Environment variable injection
- Health check considerations (can be added)

### Path C: Full-Stack Excellence

**This implementation combines both paths**:

 **Data Transformation** (Path A)
- All core transformation logic implemented
- Comprehensive error handling
- Test coverage

 **Infrastructure** (Path B)
- Docker containerization
- CLI with all arguments
- Structured logging
- Configuration management

 **Additional Features**:
- Output validation script
- Batch processing
- Retry logic with exponential backoff
- Deduplication
- Cost estimation for embeddings

---

## Testing

- Unit tests for transformers and models.
- Integration tests for the full pipeline using `tests/fixtures/raw_small.json`.
- Fake embeddings mode (`USE_FAKE_EMBEDDINGS=1`) for fast, deterministic runs.
- Optional real-embedding tests when `OPENAI_API_KEY` is provided.

Detailed test strategy, commands, and CI recommendations:
- `docs/TESTING.md`

---

## Extra Implementations

- Current pipeline is batch-oriented and in-memory; not yet streaming or distributed.
- Embeddings are generated with a single model (`text-embedding-3-small`) and no caching.
- Qdrant integration is file-based; no live DB writes yet.

A full discussion of limitations, trade-offs, and roadmap is in:
- `docs/APPROACH.md`
---

## Future Improvements

### Short Term (v1.1)

1. **Sentence-Boundary Truncation**
   ```python
   # Instead of hard cutoff at char 8000
   # Find last sentence before char 8000
   # Preserve semantic completeness
   ```

2. **Caching Layer**
   ```python
   # Cache embeddings by document hash
   # Check cache before API call
   # Estimate savings: 30-50% cost reduction
   ```

3. **Configurable Embedding Model**
   ```bash
   python -m src.run_pipeline --embedding-model text-embedding-3-large
   ```

4. **Progress Bar**
   ```python
   # Add tqdm for visual progress feedback
   for batch in tqdm(batches, desc="Embedding"):
       embeddings = embed_texts(batch)
   ```

### Medium Term (v1.2)

1. **Async Processing**
   ```python
   # Use asyncio for concurrent API calls
   # 5-10x speedup for large datasets
   ```

2. **Incremental Processing**
   ```bash
   python -m src.run_pipeline --resume-from checkpoint.json
   ```

3. **Multi-Format Support**
   - JSONL (streaming)
   - CSV/Parquet (tabular)
   - XML (structured docs)

4. **Qdrant Integration**
   ```python
   from qdrant_client import QdrantClient
   client = QdrantClient("localhost", port=6333)
   client.upload_collection(points=qdrant_points)
   ```

### Long Term (v2.0)

1. **Distributed Pipeline**
   - Kafka/Pub-Sub for event streaming
   - Horizontal scaling with multiple workers
   - Centralized orchestration (Airflow, K8s)

2. **Advanced Error Recovery**
   - Dead letter queue for failed documents
   - Retry scheduler with jitter
   - Circuit breaker pattern

3. **Monitoring & Alerting**
   - Prometheus metrics export
   - Grafana dashboards
   - PagerDuty integration

4. **Schema Evolution**
   - Handle multiple input schema versions
   - Auto-detect customer API format
   - Backward compatibility

5. **Multi-Language Support**
   - Detect document language
   - Use language-specific embeddings
   - Support non-English content

---

## Summary

This implementation represents a **production-grade data ingestion pipeline** that:

 - **Transforms** complex nested JSON into clean Qdrant format
 - **Extracts** and cleans text from HTML/markdown content
 - **Generates** vector embeddings via OpenAI API
 - **Handles** errors gracefully with detailed logging
 - **Validates** output against schema
 - **Containerizes** for reproducible deployment
 - **Tests** comprehensively with unit and integration tests
 - **Tracks** execution metadata and costs
 - **Scales** with batch processing and retry logic
 - **Documents** design decisions and trade-offs

For production deployment:
1. Install Docker and set `OPENAI_API_KEY`
2. Build image: `docker build -t capitol-pipeline:latest .`
3. Run: `docker run -e OPENAI_API_KEY=$OPENAI_API_KEY capitol-pipeline:latest`
4. Verify: Check `output/` directory for timestamped results

---

## Contact & Support

For questions or issues:
- Check `logs/pipeline.log` for detailed execution traces
- Review test files for usage examples
- Consult architecture overview for design context
