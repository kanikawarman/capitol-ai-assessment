"""Pipeline CLI Entry Point

Provides the command-line interface for running the Capitol AI data ingestion
pipeline. Handles argument parsing, logging configuration, and orchestration
of the end-to-end pipeline from raw customer API data to Qdrant-ready points.

Usage:
    python -m src.run_pipeline --input data/raw.json --output-dir output
"""

# run_pipeline.py
import argparse
import logging
from pathlib import Path

from src.capitol_pipeline.pipeline import run_pipeline

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

def configure_logging() -> None:
    """Configure logging with both console and file output.
    
    Sets up:
      - Root logger at DEBUG level
      - Console handler at INFO level for user-facing messages
      - File handler at DEBUG level for detailed troubleshooting
      - Reduced verbosity for httpx and openai loggers
    """
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "pipeline.log"

    # Root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    # Console handler: high-level INFO+
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # File handler: detailed DEBUG+
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Clear existing handlers to avoid duplicates if run multiple times
    logger.handlers.clear()
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)


def main(argv=None) -> int:
    """
    CLI entrypoint for the Capitol AI ingestion pipeline.

    Parses command-line arguments, runs the pipeline end-to-end,
    and returns a Unix-style exit code (0 on success, non-zero on failure).
    """
    configure_logging()
    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(
        description="Capitol AI Data ingestion pipeline"
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/raw_customer_api.json"),
        help="Path to raw input JSON file.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Directory where output files will be written.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit on number of documents to process.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Process data but don't upload to Qdrant"
    )
    parser.add_argument(
        "--skip-embeddings",
        action="store_true",
        help="Skip embedding generation (faster, only produces transformed docs)"
    )
    parser.add_argument(
        "--no-history",
        action="store_true",
        help="Overwrite output files instead of creating timestamped versions"
    )
    parser.add_argument(
    "--batch-size",
    type=int,
    default=100,
    help="Number of documents to process per embedding batch (default: 100)"
)
    
    args = parser.parse_args(argv)

    logger.info("=== Starting Capitol AI ingestion pipeline ===")
    logger.info("Input: %s", args.input)
    logger.info("Output directory: %s", args.output_dir)
    logger.info("Limit: %s", args.limit if args.limit else "None (all documents)")
    logger.info("Dry_run: %s", args.dry_run)
    logger.info("Skip embeddings: %s", args.skip_embeddings)
    logger.info("Keep history: %s", not args.no_history)
    
    if args.dry_run:
        logger.info("DRY RUN MODE: Will not upload to Qdrant")

    try:
        import time
        start_time = time.time()

        total_raw, processed_count, output_paths = run_pipeline(
            input_path=args.input,
            output_dir=args.output_dir,
            limit=args.limit,
            dry_run=args.dry_run,
            skip_embeddings=args.skip_embeddings,
            keep_history=not args.no_history,
            batch_size=args.batch_size
        )

        elapsed_time = time.time() - start_time

        # Comprehensive summary
        logger.info("=" * 70)
        logger.info("Pipeline completed successfully in %.2fs", elapsed_time)
        logger.info("")
        logger.info("Summary:")
        logger.info("  Input:      %s", args.input)
        logger.info("  Processed:  %d/%d documents", processed_count, total_raw)
        if args.skip_embeddings:
            logger.info("  Embeddings: Skipped")
        else:
            logger.info("  Embeddings: Generated")
        logger.info("")
        logger.info("Output files:")
        for name, path in output_paths.items():
            logger.info("  %-12s %s", f"{name}:", path)
        logger.info("=" * 70)

    except Exception as e:
        logger.exception(f"Pipeline failed with an unhandled exception: {e}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

