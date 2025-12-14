import json
from pathlib import Path
from typing import List, Dict, Any


def load_raw_documents(path: str | Path) -> List[Dict[str, Any]]:
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    # adjust based on actual structure (list or dict["docs"])
    if isinstance(data, list):
        return data
    # fall back if wrapped
    return data.get("documents") or data.get("results") or []
