from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class RawDocument(BaseModel):
    # we’ll store the raw JSON here for flexibility
    data: Dict[str, Any]


class InternalDocument(BaseModel):
    external_id: str
    title: Optional[str]
    url: Optional[str]
    published_at: Optional[str]
    categories: List[str] = []
    thumbnail_url: Optional[str]
    text: str  # cleaned content
    original: Dict[str, Any]  # full original object for debugging


class QdrantDocument(BaseModel):
    id: str
    vector: List[float]
    payload: Dict[str, Any]
