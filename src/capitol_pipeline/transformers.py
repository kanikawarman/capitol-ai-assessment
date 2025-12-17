"""Document Transformation Module

Provides text extraction, cleaning, and metadata transformation functions
for converting raw customer API documents into Qdrant-compatible format.

Key responsibilities:
  - Extract and clean text from nested content elements
  - Parse and normalize metadata fields
  - Build final documents with embeddings ready for vector storage
  - Handle edge cases and missing/malformed data gracefully
"""

import re
import html
from typing import List, Dict, Any, Optional
from .models import InternalDocument, QdrantDocument

import logging

logger = logging.getLogger(__name__)

# Regex patterns (define at module level for performance)
TAG_RE = re.compile(r'<[^>]+>')
LINK_PATTERN = re.compile(r'\[([^\]]+)\]\([^\)]+\)')  # Markdown links
HORIZONTAL_RULE = re.compile(r'^[\*\-]{3,}$', re.MULTILINE)  # ***, ---
MULTIPLE_NEWLINES = re.compile(r'\n{3,}')  # 3+ newlines
MULTIPLE_SPACES = re.compile(r' {2,}')  # 2+ spaces

def to_internal_document(raw: Dict[str, Any]) -> InternalDocument:
    """Convert raw API document to internal normalized format.
    
    Args:
        raw: Raw document dictionary from customer API
        
    Returns:
        InternalDocument with extracted and normalized fields
        
    Note:
        This is currently a placeholder. Full implementation maps all
        required fields from various possible locations in the source schema.
    """
    # placeholder; we'll fill in later
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


def clean_text_fragment(text: str) -> str:
    """
    Clean a single text fragment from a content element.
    
    Steps:
    1. Unescape HTML entities (&amp; → &, &lt; → <, etc.)
    2. Strip HTML tags
    3. Clean markdown links [text](url) → text
    4. Normalize whitespace
    
    Args:
        text: Raw text string from content element
        
    Returns:
        Cleaned text string, or empty string if nothing remains
    """
    if not text:
        return ""
    
    # 1. Unescape HTML entities
    text = html.unescape(text)
    
    # 2. Remove HTML tags
    text = TAG_RE.sub("", text)
    
    # 3. Clean markdown-style links: [text](url) → text
    text = LINK_PATTERN.sub(r"\1", text)
    
    # 4. Normalize whitespace within the fragment
    # Replace multiple spaces with single space
    text = MULTIPLE_SPACES.sub(" ", text)
    
    return text.strip()


def extract_text_from_content_elements(
    content_elements: List[Dict[str, Any]]
) -> str:
    """
    Extract and concatenate text from content elements.
    
    Only processes elements with type="text". Other types (image, raw_html,
    embed, etc.) are skipped.
    
    Args:
        content_elements: List of content element dictionaries from source doc
        
    Returns:
        Cleaned, concatenated text with paragraph breaks preserved.
        Returns empty string if no text content found.
    """
    fragments: List[str] = []
    
    for el in content_elements:
        el_type = el.get("type")
        
        # Only process text elements
        if el_type != "text":
            continue
        
        content = el.get("content", "")
        
        # Clean the fragment
        cleaned = clean_text_fragment(content)
        
        # Only include non-empty fragments
        if cleaned:
            fragments.append(cleaned)
    
    if not fragments:
        return ""
    
    # Join fragments with double newline to preserve paragraph structure
    full_text = "\n\n".join(fragments)
    
    # Post-processing: normalize the full text
    full_text = normalize_full_text(full_text)
    
    return full_text


def normalize_full_text(text: str) -> str:
    """
    Apply final normalization to the concatenated text.
    
    Steps:
    1. Remove decorative horizontal rules (*** or ---)
    2. Normalize multiple consecutive newlines (max 2)
    3. Strip leading/trailing whitespace
    
    Args:
        text: Concatenated text from all fragments
        
    Returns:
        Normalized text ready for embedding
    """
    if not text:
        return ""
    
    # Remove decorative horizontal rules
    text = HORIZONTAL_RULE.sub("", text)
    
    # Normalize multiple newlines (3+ → 2)
    # Preserves paragraph breaks but removes excessive spacing
    text = MULTIPLE_NEWLINES.sub("\n\n", text)
    
    # Final strip
    return text.strip()


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

from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


def extract_metadata(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extracts metadata for the Qdrant document schema.

    Required Fields:
      - external_id: Unique document identifier
      - url: Canonical document URL
    
    Optional String Fields (omitted if missing/empty):
      - title, website, publish_date, datetime, first_publish_date, thumb
    
    Array Fields (always present, empty [] if no data):
      - sections, categories, tags
    
    Returns:
        Dict with extracted metadata. Required fields may be None if missing
        (caller should validate).
    """
    
    # ========================================================================
    # Helper Functions
    # ========================================================================
    
    def normalize_optional_str(value: Any) -> Optional[str]:
        """Normalize to string or None. Empty strings become None."""
        if value is None or value == "":
            return None
        s = str(value).strip()
        return s if s else None
    
    def normalize_iso8601(value: Any) -> Optional[str]:
        """Normalize ISO 8601 dates, removing milliseconds if present."""
        s = normalize_optional_str(value)
        if not s:
            return None
        # Normalize "2025-07-02T00:00:00.000Z" -> "2025-07-02T00:00:00Z"
        if s.endswith(".000Z"):
            return s.replace(".000Z", "Z")
        return s
    
    def normalize_str_list(value: Any) -> List[str]:
        """Always returns a list; [] if null/missing/empty."""
        if not value:
            return []
        if isinstance(value, list):
            cleaned = [normalize_optional_str(v) for v in value]
            return [v for v in cleaned if v is not None]
        # Handle single string value
        single = normalize_optional_str(value)
        return [single] if single is not None else []
    
    # ========================================================================
    # Required Field: external_id
    # ========================================================================
    
    raw_external_id = (
        doc.get("_id")           # Primary source (real API)
        or doc.get("external_id") # Test fallback
        or doc.get("id")          # Additional fallback
    )
    external_id = str(raw_external_id) if raw_external_id is not None else None
    
    # ========================================================================
    # Required Field: url
    # ========================================================================
    
    website = normalize_optional_str(
        doc.get("website") or doc.get("canonical_website")
    )
    
    # URL resolution with base_url_map
    base_url_map = {
        "nj": "https://www.nj.com",
        "lehighvalleylive": "https://www.lehighvalleylive.com",
    }
    base_url = base_url_map.get(website, "") if website else ""
    
    # Get website_data for URL and sections extraction
    website_data = (doc.get("websites") or {}).get(website, {}) if website else {}
    
    # 1) Prefer explicit 'url' field (used in tests and some feeds)
    raw_url = doc.get("url")
    
    if not raw_url:
        # 2) Fallback: construct from website_url or canonical_url
        website_url = (
            website_data.get("website_url")
            or doc.get("website_url")
            or doc.get("canonical_url")
            or ""
        )
        
        if base_url and isinstance(website_url, str) and website_url.startswith("/"):
            raw_url = base_url + website_url
        else:
            raw_url = website_url or None
    
    url = normalize_optional_str(raw_url)
    
    # ========================================================================
    # Optional String Fields
    # ========================================================================
    
    # Title (multiple potential sources)
    title = normalize_optional_str(
        (doc.get("headlines") or {}).get("basic")
        or doc.get("headline")
        or doc.get("title")
    )
    
    # Dates from additional_properties or fallback fields
    addl = doc.get("additional_properties") or {}
    
    publish_date = normalize_iso8601(
        addl.get("publish_date") or doc.get("created_date")
    )
    
    datetime_val = normalize_iso8601(addl.get("datetime") or publish_date)
    
    first_publish_date = normalize_iso8601(
        addl.get("first_publish_date") or publish_date
    )
    
    # ========================================================================
    # Array Fields: sections
    # ========================================================================
    
    sections: List[str] = []
    
    # Extract from website_data.website_section
    ws_section = website_data.get("website_section") or {}
    
    if section_name := normalize_optional_str(ws_section.get("name")):
        sections.append(section_name)
    
    # Extract from nested site_section
    site_original = (
        ((ws_section.get("additional_properties") or {})
         .get("original") or {})
        .get("site", {})
    )
    
    if site_section := normalize_optional_str(site_original.get("site_section")):
        if site_section not in sections:
            sections.append(site_section)
    
    # Also check direct 'sections' field as fallback
    direct_sections = normalize_str_list(doc.get("sections"))
    for s in direct_sections:
        if s not in sections:
            sections.append(s)
    
    # ========================================================================
    # Array Fields: tags
    # ========================================================================
    
    tags: List[str] = []
    
    # Extract from taxonomy.tags
    for tag_obj in (doc.get("taxonomy", {}).get("tags") or []):
        if slug := normalize_optional_str(tag_obj.get("slug")):
            tags.append(slug)
    
    # Also check direct 'tags' field as fallback
    direct_tags = normalize_str_list(doc.get("tags"))
    for t in direct_tags:
        if t not in tags:
            tags.append(t)
    
    # ========================================================================
    # Array Fields: categories
    # ========================================================================
    
    categories: List[str] = []
    
    # Extract from additional_properties.product_categories.iab_taxonomy
    product_cats = (addl.get("product_categories") or {}).get("iab_taxonomy") or []
    
    for cat_entry in product_cats:
        if not cat_entry or not isinstance(cat_entry, list):
            continue
        
        label = str(cat_entry[0])
        
        # Parse "Category name: X" format
        if label.startswith("Category name:"):
            category = label.split("Category name:", 1)[1].strip()
            if category:
                categories.append(category)
    
    # Also check direct 'categories' field as fallback
    direct_categories = normalize_str_list(doc.get("categories"))
    for c in direct_categories:
        if c not in categories:
            categories.append(c)
    
    # ========================================================================
    # Optional Field: thumb (thumbnail image)
    # ========================================================================
    
    thumb: Optional[str] = None
    
    # Search content_elements for first image with thumbnailResizeUrl
    for element in (doc.get("content_elements") or []):
        if element.get("type") == "image":
            thumb_rel = (
                (element.get("additional_properties") or {})
                .get("thumbnailResizeUrl")
            )
            
            if thumb_rel := normalize_optional_str(thumb_rel):
                # Handle relative URLs
                if thumb_rel.startswith("/"):
                    thumb = base_url + thumb_rel if base_url else thumb_rel
                else:
                    thumb = thumb_rel
                break  # Use first image found
    
    # Fallback to direct 'thumb' field
    if not thumb:
        thumb = normalize_optional_str(doc.get("thumb"))
    
    # ========================================================================
    # Build Final Metadata Dictionary
    # ========================================================================
    
    metadata: Dict[str, Any] = {
        # Required fields (caller should validate these are not None)
        "external_id": external_id,
        "url": url,
        
        # Array fields (always present, empty [] if no data)
        "sections": sections,
        "categories": categories,
        "tags": tags,
    }
    
    # Optional string fields (only include if not None)
    if title is not None:
        metadata["title"] = title
    
    if website is not None:
        metadata["website"] = website
    
    if publish_date is not None:
        metadata["publish_date"] = publish_date
    
    if datetime_val is not None:
        metadata["datetime"] = datetime_val
    
    if first_publish_date is not None:
        metadata["first_publish_date"] = first_publish_date
    
    if thumb is not None:
        metadata["thumb"] = thumb
    
    return metadata


def to_qdrant_format(raw_doc: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Convert one raw article document into the simplified Qdrant format:
    {
      "text": "...",
      "metadata": { ... }
    }
    Returns None if the document has no usable text.
    """
    content_elements = raw_doc.get("content_elements") or []
    text = extract_text_from_content_elements(content_elements)
    if not text or not text.strip():
        logger.warning(
            "to_qdrant_format: rejecting doc due to missing/empty text. raw_id=%r",
            raw_doc.get("_id") or raw_doc.get("external_id") or raw_doc.get("id"),
        )
        return None

    metadata = extract_metadata(raw_doc)

    external_id = metadata.get("external_id")
    url = metadata.get("url")

    if not external_id or not isinstance(external_id, str):
        logger.warning(
            "to_qdrant_format: rejecting doc due to missing/invalid external_id. raw_id=%r",
            raw_doc.get("_id") or raw_doc.get("external_id") or raw_doc.get("id"),
        )
        return None

    if not url or not isinstance(url, str):
        logger.warning(
            "to_qdrant_format: rejecting doc due to missing/invalid url. raw_id=%r",
            raw_doc.get("_id") or raw_doc.get("external_id") or raw_doc.get("id"),
        )
        return None
    
    return {
        "text": text,
        "metadata": metadata,
    }
