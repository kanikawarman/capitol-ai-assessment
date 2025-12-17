"""Data Models Module

Defines Pydantic models for representing documents at different stages
of the pipeline: raw API responses, internal normalized format, and
Qdrant-ready documents with embeddings.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class RawDocument(BaseModel):
    """Wrapper for raw customer API response data.
    
    Stores the complete raw JSON from the source API for flexibility
    and debugging purposes.
    """
    data: Dict[str, Any]


class InternalDocument(BaseModel):
    """Internal normalized document format.
    
    Represents a document after transformation from raw API format.
    Contains extracted and cleaned content, metadata, and reference
    to the original document for debugging.
    """
    external_id: str
    title: Optional[str]
    url: Optional[str]
    published_at: Optional[str]
    categories: List[str] = []
    thumbnail_url: Optional[str]
    text: str  # cleaned content
    original: Dict[str, Any]  # full original object for debugging


class QdrantDocument(BaseModel):
    """Qdrant-ready document with embedding vector.
    
    Final format for ingestion into Qdrant vector database.
    Contains document ID, embedding vector, and payload with
    text and metadata for filtering and retrieval.
    """
    id: str
    vector: List[float]
    payload: Dict[str, Any]
