"""
Qdrant Collection Configuration (design-only)

This module documents the intended Qdrant collection schema and
ingestion strategy. It is **not** used at runtime in this assessment –
the pipeline only writes JSON files. In a real deployment, this config
would be used to create the collection and upsert points.
"""

# --- Core collection settings ---

QDRANT_COLLECTION_NAME = "news_articles"

# Must match the embedding model used in embeddings.py
QDRANT_VECTOR_SIZE = 1536          # text-embedding-3-small
QDRANT_DISTANCE = "Cosine"         # or "Dot" / "Euclidean"


# --- Payload / schema design (informational) ---

QDRANT_PAYLOAD_SCHEMA = {
    "text": "Full document text (string)",

    # Required metadata
    "external_id": "Unique id from source system (string)",
    "url": "Canonical URL (string)",

    # Optional metadata
    "title": "Title (string, optional)",
    "website": "Website slug, e.g. 'nj', 'lehighvalleylive' (string, optional)",
    "sections": "List[str], optional; [] when missing",
    "categories": "List[str], optional; [] when missing",
    "tags": "List[str], optional; [] when missing",
    "publish_date": "ISO-8601 string, optional",
    "datetime": "ISO-8601 string, optional",
    "first_publish_date": "ISO-8601 string, optional",
    "thumb": "Thumbnail URL (string, optional)",
}

# Fields worth indexing in Qdrant for filtering
QDRANT_INDEXED_FIELDS = [
    "external_id",   # primary key / upsert id
    "website",       # filter by source
    "sections",      # filter by section
    "publish_date",  # date range queries
]


# --- Ingestion / upsert strategy (design) ---

QDRANT_UPSERT_STRATEGY = {
    "strategy": "upsert",
    "primary_key": "external_id",
    "behavior": {
        "new_document": "insert new point",
        "existing_document": "update vector + payload for that id",
    },
    "benefits": [
        "Idempotent re-runs of the pipeline",
        "Automatic handling of updated articles",
        "No duplicate documents for the same external_id",
    ],
}


# --- Collection organization ---

QDRANT_COLLECTION_STRATEGY = {
    "mode": "single_collection_with_filtering",
    "collection_name": QDRANT_COLLECTION_NAME,
    "filtering": "Use payload.website, sections, tags to filter results",
    "rationale": (
        "Simpler to operate for this project; cross-website search is possible "
        "in a single query. Multi-collection per website can be added later "
        "if scale or isolation requires it."
    ),
}
