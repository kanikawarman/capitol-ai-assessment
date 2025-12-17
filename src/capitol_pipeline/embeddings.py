"""Embeddings Generation Module

Generates vector embeddings for document text using OpenAI's embedding API.
Handles text truncation, batching, rate limiting, and comprehensive error
handling to ensure reliable embedding generation at scale.

Key features:
  - Text truncation to fit embedding model context window
  - Batch processing for API efficiency
  - Exponential backoff retry logic for rate limiting
  - Fake embeddings mode for testing without API calls
  - Detailed logging and validation

Environment variables:
  OPENAI_API_KEY: Required API key for OpenAI (defaults to None)
  USE_FAKE_EMBEDDINGS: Set to '1' to use fake vectors for testing
  MAX_EMBEDDING_CHARS: Maximum characters per text (default: 8000)
"""

from typing import List
import os
import time
import logging

import openai                    
from openai import OpenAI

logger = logging.getLogger(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
USE_FAKE_EMBEDDINGS = os.getenv("USE_FAKE_EMBEDDINGS", "0") == "1"

EMBEDDING_MODEL = "text-embedding-3-small"

# Conservative character limit to stay well under OpenAI's 8191 token limit
# (~4 chars/token average, using 8000 chars gives ~2000 tokens = safe margin)
MAX_EMBEDDING_CHARS = int(os.getenv("MAX_EMBEDDING_CHARS", "8000"))


def _truncate_for_embedding(text: str, max_chars: int = MAX_EMBEDDING_CHARS) -> str:
    """
    Truncate text to fit embedding model's context window.
    
    Strategy:
    - If text <= max_chars: return as-is
    - If text > max_chars: truncate at max_chars, then backtrack to last space
      to avoid breaking words (if space found in last 20% of truncated text)
    
    Args:
        text: Input text to truncate
        max_chars: Maximum characters to keep
        
    Returns:
        Truncated text, guaranteed to be <= max_chars characters
        
    Note:
        Using character-based truncation (~4 chars per token average) provides
        a safe margin below OpenAI's 8191 token limit while being significantly
        faster than tokenization.
    """
    if not text:
        return ""
    
    if len(text) <= max_chars:
        return text
    
    original_len = len(text)
    truncated = text[:max_chars]
    
    # Try to avoid cutting mid-word by backtracking to last space
    # Only backtrack if space is in last 20% (avoids over-truncating)
    last_space = truncated.rfind(" ")
    if last_space > int(max_chars * 0.8):
        truncated = truncated[:last_space]
    
    logger.info(
        "Truncated text for embedding: %d -> %d chars (%.1f%% reduction)",
        original_len,
        len(truncated),
        100 * (original_len - len(truncated)) / original_len,
    )
    
    return truncated


def embed_texts(
    texts: List[str],
    model: str = EMBEDDING_MODEL,
    batch_size: int = 50,
    max_chars: int = MAX_EMBEDDING_CHARS,
) -> List[List[float]]:
    """
    Generate embeddings for texts using OpenAI's API.
    
    Features:
    - Batches requests for efficiency (default: 50 texts per call)
    - Auto-truncates long texts to fit model context window
    - Validates embedding dimensionality consistency
    - Comprehensive error handling and logging
    
    Args:
        texts: List of text strings to embed
        model: OpenAI embedding model (default: text-embedding-3-small)
        batch_size: Number of texts per API call
        max_chars: Character limit per text (default: 8000)
        
    Returns:
        List of embedding vectors (each a list of floats)
        
    Raises:
        ValueError: If embedding dimensions are inconsistent
        Exception: On OpenAI API errors
    """
    if not texts:
        logger.debug("embed_texts called with empty list; returning []")
        return []
    
    if USE_FAKE_EMBEDDINGS:
        logger.warning(
            "USE_FAKE_EMBEDDINGS=1 set; returning fake zero vectors instead of "
            "calling OpenAI. This is intended for local/dev when quota is exhausted."
        )
        # simple fixed-dim vector, e.g. dim=8
        dim = 8
        return [[0.0] * dim for _ in texts]
    
    # Apply truncation to ensure all texts fit in context window
    processed_texts = [
        _truncate_for_embedding(text, max_chars) for text in texts
    ]
    vectors: List[List[float]] = []
    
    try:
        for start in range(0, len(processed_texts), batch_size):
            batch = processed_texts[start : start + batch_size]
            end = start + len(batch) - 1
            
            logger.debug(
                "Calling OpenAI embeddings API: model=%s, batch=[%d:%d], size=%d",
                model, start, end, len(batch)
            )
            
            response = client.embeddings.create(
                model=model,
                input=batch,
            )
            
            batch_vectors = [list(item.embedding) for item in response.data]
            vectors.extend(batch_vectors)
            
            logger.debug(
                "Batch [%d:%d] completed: received %d vectors",
                start, end, len(batch_vectors)
            )
        
        # Validate dimensionality consistency
        if vectors:
            expected_dim = len(vectors[0])
            for idx, vec in enumerate(vectors):
                if len(vec) != expected_dim:
                    raise ValueError(
                        f"Inconsistent embedding dimension at index {idx}: "
                        f"expected {expected_dim}, got {len(vec)}"
                    )
        
        logger.info(
            "Successfully generated %d embeddings (dim=%d)",
            len(vectors), len(vectors[0]) if vectors else 0
        )
        
        return vectors
    
    except Exception:
        logger.exception(
            "Failed to generate embeddings for %d texts", len(texts)
        )
        raise

def embed_texts_with_retry(
    texts: List[str],
    model: str = EMBEDDING_MODEL,
    batch_size: int = 50,
    max_chars: int = MAX_EMBEDDING_CHARS,
    max_retries: int = 5,
) -> List[List[float]]:
    """
    Wraps embed_texts to handle rate limiting with retries.
    Retries up to `max_retries` times with exponential backoff.
    """
    retries = 0
    while True:
        try:
            return embed_texts(texts, model=model, batch_size=batch_size, max_chars=max_chars)
        except openai.RateLimitError as e:  # <-- use openai.RateLimitError
            retries += 1
            # For pure "insufficient_quota" errors, retries won’t help – fail fast
            if getattr(e, "code", None) == "insufficient_quota" or "insufficient_quota" in str(e):
                logger.error("Insufficient quota – cannot retry. Error: %s", e)
                raise

            if retries > max_retries:
                logger.error(
                    "Max retries exceeded (%d). Last error: %s",
                    max_retries,
                    e,
                )
                raise

            wait_time = 2 ** retries
            logger.warning(
                "Rate limit error from OpenAI (attempt %d/%d). "
                "Sleeping for %d seconds before retry. Error: %s",
                retries,
                max_retries,
                wait_time,
                e,
            )
            time.sleep(wait_time)

