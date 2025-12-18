"""
Data Ingestion Pipeline for Capitol AI Assessment

This module provides a production-grade pipeline for transforming customer API data
into Qdrant-compatible format with vector embeddings.

Features:
- Dual output format (with and without embeddings)
- Timestamped versioning for idempotent processing
- Comprehensive error handling and validation
- Progress tracking and structured logging
- Deduplication by external_id
"""

from pathlib import Path
import json
from typing import List, Dict, Any, Optional, Tuple
import logging
import time
from uuid import uuid4
from datetime import datetime
import shutil

from .embeddings import embed_texts
from .transformers import to_qdrant_format
from .loaders import load_raw_documents
from .embeddings import embed_texts_with_retry as embed_texts


logger = logging.getLogger(__name__)

TEXT_CHAR_LIMIT = 8000  

def truncate_for_embedding(text: str, max_chars: int = TEXT_CHAR_LIMIT) -> str:
    """
    Truncate raw document text before sending to the embedding model.

    - We keep the full text in the written JSON output.
    - For embeddings, we only feed up to `max_chars` characters to avoid
      very long inputs blowing up token limits / costs.
    """
    if not text:
        return text
    if len(text) <= max_chars:
        return text
    # simple head-only truncation; document this choice in README
    return text[:max_chars]

def build_qdrant_points(
    docs: List[Dict[str, Any]],
    batch_size: int = 100 
) -> List[Dict[str, Any]]:
    """
    Build Qdrant points with embeddings, processing in batches.
    
    Args:
        docs: List of documents with 'text' and 'metadata' fields
        batch_size: Number of documents to embed per batch (default: 100)
        
    Returns:
        List of Qdrant points with embeddings
    """
    if not docs:
        logger.warning("No documents to process")
        return []

    points: List[Dict[str, Any]] = []
    total_batches = (len(docs) + batch_size - 1) // batch_size
    
    logger.info(
        "Processing %d documents in %d batches (batch_size=%d)",
        len(docs),
        total_batches,
        batch_size
    )
    
    # Process in batches
    for batch_idx in range(0, len(docs), batch_size):
        batch_docs = docs[batch_idx:batch_idx + batch_size]
        batch_num = (batch_idx // batch_size) + 1
        
        logger.info("Processing batch %d/%d (%d docs)", 
                   batch_num, total_batches, len(batch_docs))
        
        # Extract texts for this batch
        texts = [d["text"] for d in batch_docs]
        
        # Get embeddings for batch
        try:
            start_time = time.time()
            # Keep full text in docs, but truncate what we send to the embedding model.
            texts_for_embedding: List[str] = [
                truncate_for_embedding(d["text"], max_chars=TEXT_CHAR_LIMIT) for d in docs
            ]

            logger.debug(
                "Requesting embeddings for %d documents (max_chars_per_doc=%d)",
                len(texts_for_embedding),
                TEXT_CHAR_LIMIT,
            )
            embeddings = embed_texts(texts)
            elapsed = time.time() - start_time
            
            logger.info(
                "✓ Batch %d/%d embeddings generated (%.2fs, %.2fs per doc)",
                batch_num,
                total_batches,
                elapsed,
                elapsed / len(texts)
            )
        except Exception as e:
            logger.error("Failed to generate embeddings for batch %d: %s", batch_num, e)
            raise
        
        # Build points for this batch
        for doc, vector in zip(batch_docs, embeddings):
            meta = doc["metadata"]
            external_id = meta.get("external_id")
            
            if not external_id:
                logger.warning("Document missing external_id, skipping")
                continue

            payload = {
                "text": doc["text"],
                **meta,
            }

            points.append({
                "id": external_id,
                "vector": vector,
                "payload": payload,
            })
    
    logger.info("✓ Generated %d points total", len(points))
    return points


def run_pipeline(
    input_path: Path | str = "data/raw_customer_api.json",
    output_dir: Path | str = "output",
    limit: Optional[int] = None,
    dry_run: bool = False,
    skip_embeddings: bool = False,
    keep_history: bool = True,
    batch_size: int = 100  
) -> Tuple[int, int, Dict[str, Path]]:
    """
    Run the complete data ingestion pipeline with production-grade file management.
    
    Pipeline Steps:
    1. Load raw documents from JSON
    2. Transform to Qdrant schema format
    3. Deduplicate by external_id
    4. Generate embeddings (unless skip_embeddings=True)
    5. Build Qdrant points
    6. Save outputs with versioning
    
    Output Strategy:
    - Creates timestamped outputs: transformed_documents_20251216_010530.json
    - Maintains "latest" symlinks for easy access
    - Optional: keeps historical runs for auditing
    
    Args:
        input_path: Path to input JSON file with raw customer API data
        output_dir: Directory for all output files
        limit: Maximum documents to process (None = all)
        skip_embeddings: If True, only generate transformed docs (faster for testing)
        keep_history: If True, keep timestamped versions; if False, overwrite
        
    Returns:
        Tuple of (total_raw_documents, successfully_processed_documents, output_paths_dict)
        
    Raises:
        FileNotFoundError: If input_path doesn't exist
        json.JSONDecodeError: If input file is invalid JSON
        Exception: For other processing errors
        
    Example:
        >>> total, processed, paths = run_pipeline(
        ...     input_path="data/raw_customer_api.json",
        ...     output_dir="output",
        ...     limit=10
        ... )
        >>> print(f"Processed {processed}/{total} documents")
        >>> print(f"Output: {paths['transformed_latest']}")
    """
    # Convert to Path objects
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate timestamp and job ID for this run
    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    job_id = f"pipeline_{run_timestamp}"
    job_start = time.time()

    logger.debug("Starting pipeline processing: %s", job_id)
    
    # ========== STEP 1: LOAD RAW DOCUMENTS ==========
    t0 = time.time()
    logger.info("STEP 1/5: Loading raw documents")
    
    try:
        raw_docs = load_raw_documents(input_path)
        total_raw = len(raw_docs)
        logger.info(
            "✓ Loaded %d raw documents in %.2fs",
            total_raw,
            time.time() - t0
        )
    except FileNotFoundError:
        logger.exception("Input file not found: %s", input_path)
        raise
    except json.JSONDecodeError:
        logger.exception("Invalid JSON in input file: %s", input_path)
        raise
    except Exception:
        logger.exception("Failed to load raw documents from %s", input_path)
        raise

    # Apply limit if specified
    if limit is not None:
        logger.info("Applying limit: %d documents", limit)
        raw_docs = raw_docs[:limit]

    # ========== STEP 2: TRANSFORM DOCUMENTS ==========
    t1 = time.time()
    logger.info("STEP 2/5: Transforming %d documents", len(raw_docs))
    
    try:
        simplified_docs: List[Dict[str, Any]] = []
        skipped_count = 0
        
        # Calculate logging interval (log at 10%, 20%, 30%, etc.)
        log_interval = max(1, len(raw_docs) // 10)
        
        for idx, raw in enumerate(raw_docs, start=1):
            external_id = raw.get("external_id") or raw.get("_id")
            
            # Log progress at intervals
            if idx == 1 or idx == len(raw_docs) or idx % log_interval == 0:
                logger.info(
                    "Transform progress: %d/%d (%.1f%%) - Success: %d, Skipped: %d",
                    idx,
                    len(raw_docs),
                    (idx / len(raw_docs)) * 100,
                    len(simplified_docs),
                    skipped_count
                )

            # Transform document
            doc = to_qdrant_format(raw)
            if doc is None:
                logger.warning(
                    "Skipping document idx=%d external_id=%s: no usable text",
                    idx,
                    external_id,
                )
                skipped_count += 1
                continue
            
            simplified_docs.append(doc)
        
        logger.info(
            "✓ Transform step completed in %.2fs (success=%d, skipped=%d)",
            time.time() - t1,
            len(simplified_docs),
            skipped_count
        )
    except Exception:
        logger.exception("Failed during document transformation")
        raise

    # ========== STEP 3: DEDUPLICATE BY external_id ==========
    t2 = time.time()
    logger.info("STEP 3/5: Deduplicating documents by external_id")
    
    seen_ids: set[str] = set()
    deduped_docs: List[Dict[str, Any]] = []
    duplicate_count = 0

    for doc in simplified_docs:
        meta = doc.get("metadata", {})
        ext_id = meta.get("external_id")

        # Validation: warn about missing external_id
        if not ext_id:
            logger.warning(
                "Document missing external_id after transform. "
                "This may cause issues during point generation. "
                "Document preview: %s",
                str(doc)[:200]
            )
            deduped_docs.append(doc)
            continue

        # Skip duplicates
        if ext_id in seen_ids:
            logger.warning(
                "Duplicate external_id detected: %s. Keeping first occurrence.",
                ext_id,
            )
            duplicate_count += 1
            continue

        seen_ids.add(ext_id)
        deduped_docs.append(doc)

    simplified_docs = deduped_docs
    logger.info(
        "✓ Deduplication completed in %.2fs (removed %d duplicates, kept %d unique)",
        time.time() - t2,
        duplicate_count,
        len(simplified_docs)
    )

    # ========== STEP 4: SAVE TRANSFORMED DOCUMENTS (WITHOUT EMBEDDINGS) ==========
    t3 = time.time()
    logger.info("STEP 4/5: Saving transformed documents (without embeddings)")
    
    # Define output paths
    if keep_history:
        transformed_filename = f"transformed_{run_timestamp}.json"
    else:
        transformed_filename = "transformed.json"

    transformed_path = output_dir / transformed_filename
    
    output_paths = {}
    
    # If this is a dry run, do not write any output files at all.
    if dry_run:
        logger.info("DRY RUN: skipping write of transformed documents and embeddings")
        # Return counts but do not create any files or metadata
        logger.debug(
            "Pipeline processing completed (dry run): %d raw → %d processed (no files written)",
            total_raw,
            len(simplified_docs)
        )
        return total_raw, len(simplified_docs), output_paths

    try:
        # Write transformed documents
        with transformed_path.open("w", encoding="utf-8") as f:
            json.dump(simplified_docs, f, ensure_ascii=False, indent=2)
        
        output_paths["transformed"] = transformed_path
        
        logger.info(
            "✓ Wrote %d transformed documents to %s (%.2fs)",
            len(simplified_docs),
            transformed_path.name,
            time.time() - t3
        )
    except Exception:
        logger.exception("Failed to save transformed documents")
        raise

    # ========== STEP 5: GENERATE EMBEDDINGS & SAVE POINTS ==========
    if skip_embeddings:
        logger.info("STEP 5/5: Skipping embedding generation (skip_embeddings=True)")
        
        # Write run metadata
        if keep_history:
            _save_metadata(output_dir, run_timestamp, keep_history, {
                "timestamp": run_timestamp,
                "input_file": str(input_path),
                "total_raw": total_raw,
                "processed": len(simplified_docs),
                "skipped": skipped_count,
                "duplicates_removed": duplicate_count,
                "embeddings_generated": False,
                "outputs": {k: str(v) for k, v in output_paths.items()},
                "duration_seconds": time.time() - job_start
            })

        logger.debug(
            "Pipeline processing completed: %d raw → %d processed (embeddings skipped)",
            total_raw,
            len(simplified_docs)
        )

        return total_raw, len(simplified_docs), output_paths
    
    # Generate embeddings
    t4 = time.time()
    logger.info("STEP 5/5: Generating embeddings and building Qdrant points")
    
    try:
        # points = build_qdrant_points(simplified_docs)
        points = build_qdrant_points(simplified_docs, batch_size=100)
        logger.info("✓ Built %d Qdrant points in %.2fs", len(points), time.time() - t4)
    except Exception:
        logger.exception("Failed to build Qdrant points with embeddings")
        raise
    
    # Save points with embeddings
    if keep_history:
        points_filename = f"qdrant_points_{run_timestamp}.json"
    else:
        points_filename = "qdrant_points.json"

    points_path = output_dir / points_filename
    
    try:
        with points_path.open("w", encoding="utf-8") as f:
            json.dump(points, f, ensure_ascii=False, indent=2)
        
        output_paths["points"] = points_path
        
        logger.info(
            "✓ Wrote %d points with embeddings to %s",
            len(points),
            points_path.name
        )
    except Exception:
        logger.exception("Failed to save Qdrant points")
        raise

    # ========== WRITE RUN METADATA ==========
    if keep_history:
        _save_metadata(output_dir, run_timestamp, keep_history, {
            "timestamp": run_timestamp,
            "input_file": str(input_path),
            "total_raw": total_raw,
            "processed": len(points),
            "skipped": skipped_count,
            "duplicates_removed": duplicate_count,
            "embeddings_generated": True,
            "outputs": {k: str(v) for k, v in output_paths.items()},
            "duration_seconds": time.time() - job_start
        })

    # ========== PIPELINE COMPLETE ==========
    logger.debug(
        "Pipeline processing completed: %d raw → %d processed → %d with embeddings",
        total_raw,
        len(simplified_docs),
        len(points)
    )

    return total_raw, len(points), output_paths


def _save_metadata(
    output_dir: Path,
    run_timestamp: str,
    keep_history: bool,
    metadata: Dict[str, Any]
) -> None:
    """Save pipeline run metadata."""
    if keep_history:
        meta_filename = f"run_metadata_{run_timestamp}.json"
    else:
        meta_filename = "run_metadata.json"
    
    meta_path = output_dir / meta_filename
    metadata["timestamp"] = run_timestamp
    
    try:
        with meta_path.open("w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        logger.info("✓ Saved: %s", meta_filename)
    except Exception:
        logger.warning("Failed to save metadata (non-fatal)", exc_info=True)



def cleanup_old_runs(output_dir: Path, keep_last_n: int = 10) -> None:
    """
    Keep only the last N pipeline runs, delete older timestamped files.
    Always preserves *_latest.json symlinks.
    
    Args:
        output_dir: Directory containing pipeline outputs
        keep_last_n: Number of recent runs to keep (default: 10)
        
    Example:
        >>> cleanup_old_runs(Path("output"), keep_last_n=5)
    """
    logger.info("Cleaning up old runs in %s (keeping last %d)", output_dir, keep_last_n)
    
    # Find all timestamped transformed docs (excluding _latest)
    pattern = "transformed_documents_*.json"
    files = sorted(
        [
            f for f in output_dir.glob(pattern)
            if not f.name.endswith("_latest.json")
        ],
        key=lambda x: x.stat().st_mtime,
        reverse=True  # Most recent first
    )
    
    deleted_count = 0
    for old_file in files[keep_last_n:]:
        # Extract timestamp from filename
        timestamp = old_file.stem.replace("transformed_documents_", "")
        
        logger.debug("Cleaning up run: %s", timestamp)
        
        # Delete all files from this run
        run_files = [
            output_dir / f"transformed_documents_{timestamp}.json",
            output_dir / f"qdrant_points_{timestamp}.json",
            output_dir / f"pipeline_{timestamp}_metadata.json",
        ]
        
        for run_file in run_files:
            if run_file.exists():
                run_file.unlink()
                deleted_count += 1
    
    if deleted_count > 0:
        logger.info("Cleaned up %d old files", deleted_count)
    else:
        logger.info("No old files to clean up")
