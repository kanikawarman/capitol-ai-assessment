"""Data Loader Module

Provides utilities to load raw customer API data from JSON files.
Supports flexible schema detection for documents wrapped in various
container structures (flat array, 'documents' key, 'results' key, etc.).
"""

import json
from pathlib import Path
from typing import List, Dict, Any


def load_raw_documents(path: str | Path) -> List[Dict[str, Any]]:
    """Load raw documents from a JSON file.
    
    Supports flexible input formats:
      - Direct list of documents: [{...}, {...}, ...]
      - Wrapped in 'documents' key: {"documents": [...]}
      - Wrapped in 'results' key: {"results": [...]}
    
    Args:
        path: File path to JSON file containing raw documents
        
    Returns:
        List of raw document dictionaries
        
    Raises:
        FileNotFoundError: If file does not exist
        json.JSONDecodeError: If file is not valid JSON
    """
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    # fall back if wrapped
    return data.get("documents") or data.get("results") or []
