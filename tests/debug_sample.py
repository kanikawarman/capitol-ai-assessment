import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from src.capitol_pipeline.transformers import to_qdrant_format

def main():
    sample_path = Path("data/raw_sample.json")
    with sample_path.open("r", encoding="utf-8") as f:
        raw_docs = json.load(f)

    out_docs = []
    for raw in raw_docs:
        doc = to_qdrant_format(raw)
        if doc is not None:
            out_docs.append(doc)

    output_path = Path("output/sample_qdrant_like.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(out_docs, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(out_docs)} docs to {output_path}")

if __name__ == "__main__":
    main()
