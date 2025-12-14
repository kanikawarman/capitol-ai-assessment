from typing import List, Dict, Any
from .models import InternalDocument, QdrantDocument


def to_internal_document(raw: Dict[str, Any]) -> InternalDocument:
    """
    Map one raw JSON document into our normalized InternalDocument.
    TODO: implement field mapping + content extraction.
    """
    # placeholder; we’ll fill in later
    return InternalDocument(
        external_id=str(raw.get("id") or raw.get("_id") or ""),
        title=raw.get("headlines", {}).get("basic") if isinstance(raw.get("headlines"), dict) else raw.get("title"),
        url=raw.get("canonical_url"),
        published_at=raw.get("publish_date") or raw.get("created_date"),
        categories=[],  # TODO: map from taxonomies/sections
        thumbnail_url=None,  # TODO: map from promo items
        text="",  # TODO: extract from content_elements
        original=raw,
    )


def to_qdrant_document(
    internal_doc: InternalDocument,
    vector: List[float],
) -> QdrantDocument:
    """
    Build a Qdrant-compatible document based on qdrant_schema.md.
    """
    payload = {
        "external_id": internal_doc.external_id,
        "title": internal_doc.title,
        "url": internal_doc.url,
        "published_at": internal_doc.published_at,
        "categories": internal_doc.categories,
        "thumbnail_url": internal_doc.thumbnail_url,
        "text": internal_doc.text,
        # you can embed extra metadata here as needed
    }
    return QdrantDocument(
        id=internal_doc.external_id,
        vector=vector,
        payload=payload,
    )
