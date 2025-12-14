from pathlib import Path
import json
from typing import Iterable

from .loaders import load_raw_documents
from .transformers import to_internal_document, to_qdrant_document
from .embeddings import embed_text


def run_pipeline(
    input_path: str | Path = "data/raw_sample.json",
    output_path: str | Path = "output/transformed_documents.json",
    limit: int | None = None,
):
    raw_docs = load_raw_documents(input_path)

    if limit is not None:
        raw_docs = raw_docs[:limit]

    qdrant_docs = []
    for raw in raw_docs:
        internal = to_internal_document(raw)
        if not internal.text:
            # we’ll improve this later after we implement text extraction
            continue
        vector = embed_text(internal.text)
        qdrant_doc = to_qdrant_document(internal, vector)
        qdrant_docs.append(qdrant_doc.model_dump())

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(qdrant_docs, f, ensure_ascii=False, indent=2)
