import copy
import json
from pathlib import Path

from src.capitol_pipeline.transformers import (
    extract_text_from_content_elements,
    extract_metadata,
    to_qdrant_format,
)


# --- helpers -----------------------------------------------------------------


def load_sample_docs():
    path = Path("data/raw_sample.json")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_first_sample():
    return load_sample_docs()[0]


# --- extract_text_from_content_elements --------------------------------------


def test_extract_text_not_empty_on_real_sample():
    """Sanity check: on a real sample doc, we get a non-trivial text string."""
    raw = load_first_sample()
    text = extract_text_from_content_elements(raw.get("content_elements", []))

    assert isinstance(text, str)
    # arbitrary sanity threshold so it's not just a tiny string
    assert len(text) > 100


def test_extract_text_concatenates_multiple_text_elements():
    """Multiple text content elements should be concatenated in order."""
    content_elements = [
        {"type": "text", "content": "First paragraph."},
        {"type": "text", "content": "Second paragraph."},
        # non-text elements should be ignored
        {"type": "image", "url": "http://example.com/img.png"},
        {"type": "text", "content": "Third paragraph."},
    ]

    text = extract_text_from_content_elements(content_elements)

    assert "First paragraph." in text
    assert "Second paragraph." in text
    assert "Third paragraph." in text
    # preserve order (simple check: 'First' comes before 'Second')
    assert text.index("First paragraph.") < text.index("Second paragraph.")

def test_extract_text_strips_html_tags_and_decodes_entities():
    """
    HTML tags should be stripped and HTML entities (&amp;) should be decoded
    in the final combined text.
    """
    content_elements = [
    {
        "type": "text",
        "content": "<p>Hello &amp; <b>world</b></p>",
    },
    # non-text elements should be ignored
    {
        "type": "image",
        "content": "<img src='foo.jpg' />",
    },
    ]

    text = extract_text_from_content_elements(content_elements)

    # We expect:
    # - <p> and <b> tags removed
    # - &amp; decoded to &
    # - No extra whitespace
    assert text == "Hello & world"

def test_extract_text_ignores_empty_or_none_content():
    """Empty / None content elements should not produce junk text."""
    content_elements = [
        {"type": "text", "content": "  "},
        {"type": "text", "content": None},
        {"type": "text", "content": "Actual text."},
    ]

    text = extract_text_from_content_elements(content_elements)

    assert text.strip() == "Actual text."


# --- extract_metadata ---------------------------------------------------------


def test_metadata_has_core_fields_from_real_sample():
    """On a real sample, we should have core metadata fields present."""
    raw = load_first_sample()
    meta = extract_metadata(raw)

    assert meta["external_id"]
    assert meta["url"]
    assert meta["website"]
    # title might come from headlines/basic or title field
    assert meta.get("title")


def test_metadata_missing_optional_fields_is_ok():
    """
    Removing optional fields (like thumb/tags) should not break metadata
    extraction. We only require core identity fields.
    """
    raw = load_first_sample()
    raw_copy = copy.deepcopy(raw)

    # Simulate optional fields being absent
    raw_copy.pop("tags", None)
    raw_copy.pop("sections", None)
    raw_copy.pop("promo_items", None)

    meta = extract_metadata(raw_copy)

    # Core identity fields still present
    assert meta["external_id"]
    assert meta["url"]
    assert meta["website"]


# --- to_qdrant_format --------------------------------------------------------


def test_to_qdrant_format_minimal_valid_doc():
    """
    Minimal valid raw doc with required fields should produce a Qdrant-style
    intermediate dict: {'text': ..., 'metadata': {...}}.
    """
    raw = {
        "external_id": "doc-123",
        "title": "Minimal title",
        "url": "http://example.com/minimal",
        "website": "example",
        "content_elements": [
            {"type": "text", "content": "Some body text here."},
        ],
    }

    doc = to_qdrant_format(raw)
    assert doc is not None

    assert "text" in doc
    assert "metadata" in doc
    assert isinstance(doc["text"], str)
    assert isinstance(doc["metadata"], dict)

    # Core metadata presence
    meta = doc["metadata"]
    assert meta["external_id"] == "doc-123"
    assert meta["url"] == "http://example.com/minimal"
    assert meta.get("title")  # from title or headlines.basic


def test_to_qdrant_format_handles_missing_optional_fields():
    """
    If optional fields (thumb, tags, sections, etc.) are missing, the transform
    should still succeed and return text + metadata.
    """
    raw = {
        "external_id": "doc-456",
        "title": "Title without extras",
        "url": "http://example.com/no-optional",
        "website": "example",
        # no thumb, no tags, no sections, etc.
        "content_elements": [
            {"type": "text", "content": "Body text without extras."},
        ],
    }

    doc = to_qdrant_format(raw)
    assert doc is not None
    meta = doc["metadata"]

    assert meta["external_id"] == "doc-456"
    assert meta["url"] == "http://example.com/no-optional"
    assert meta["website"] == "example"


def test_to_qdrant_format_missing_required_text_returns_none():
    """
    If there is no usable text (no content_elements or only empty content),
    to_qdrant_format should return None so the pipeline can skip this doc.
    """
    raw_no_elements = {
        "external_id": "doc-empty-1",
        "title": "No content elements",
        "url": "http://example.com/empty1",
        "website": "example",
        "content_elements": [],
    }

    raw_only_empty = {
        "external_id": "doc-empty-2",
        "title": "Only whitespace content",
        "url": "http://example.com/empty2",
        "website": "example",
        "content_elements": [
            {"type": "text", "content": "   "},
            {"type": "text", "content": "\n\n"},
        ],
    }

    assert to_qdrant_format(raw_no_elements) is None
    assert to_qdrant_format(raw_only_empty) is None


def test_to_qdrant_format_trims_or_normalizes_text():
    """
    Leading/trailing whitespace in content elements should be stripped in
    the final text output.
    """
    raw = {
        "external_id": "doc-789",
        "title": "Whitespace title",
        "url": "http://example.com/whitespace",
        "website": "example",
        "content_elements": [
            {"type": "text", "content": "   First line.   "},
            {"type": "text", "content": "\n  Second line.\n"},
        ],
    }

    doc = to_qdrant_format(raw)
    assert doc is not None

    text = doc["text"]
    # Very loose check: no leading/trailing whitespace, but both sentences present
    assert text.startswith("First line.")
    assert "Second line." in text
    assert not text.startswith(" ")
    assert not text.endswith(" ")


def test_to_qdrant_format_preserves_external_id_in_metadata():
    """
    external_id from the raw doc must appear in the metadata so build_qdrant_points
    can later use it as the Qdrant point id.
    """
    raw = {
        "external_id": "doc-preserve-id",
        "title": "Preserve external id",
        "url": "http://example.com/preserve-id",
        "website": "example",
        "content_elements": [
            {"type": "text", "content": "Some text."},
        ],
    }

    doc = to_qdrant_format(raw)
    assert doc is not None

    meta = doc["metadata"]
    assert meta["external_id"] == "doc-preserve-id"

def test_to_qdrant_format_maps_optional_metadata_fields():
    """
    If optional fields (title, website, sections, categories, tags, thumb) are present
    in the raw doc, they should appear correctly in metadata.
    """
    raw = {
        "_id": "doc-optional",
        "title": "Optional fields title",
        "url": "http://example.com/optional",
        "website": "example-site",
        "sections": ["News", "Local"],
        "categories": ["Category1"],
        "tags": ["tag1", "tag2"],
        "thumb": "http://example.com/thumb.jpg",
        "content_elements": [
            {"type": "text", "content": "Some optional fields body text."},
        ],
    }

    doc = to_qdrant_format(raw)
    assert doc is not None

    meta = doc["metadata"]
    assert meta["external_id"] == "doc-optional"
    assert meta["url"] == "http://example.com/optional"
    assert meta["website"] == "example-site"

    assert meta["sections"] == ["News", "Local"]
    assert meta["categories"] == ["Category1"]
    assert meta["tags"] == ["tag1", "tag2"]
    assert meta["thumb"] == "http://example.com/thumb.jpg"

def test_extract_metadata_omits_null_or_empty_optional_strings():
    """
    Optional string fields (title, thumb, website, dates) must be omitted,
    not set to "" or null, when they are missing/empty.
    """
    raw = {
        "_id": "doc-no-optional-strings",
        "url": "http://example.com/no-strings",
        "website": "",     # empty -> should be omitted
        "title": "   ",    # whitespace -> omitted
        "thumb": None,     # null -> omitted
        "additional_properties": {
            "publish_date": "",          # empty -> omitted
            "first_publish_date": None,  # null -> omitted
        },
    }

    meta = extract_metadata(raw)

    # Required
    assert meta["external_id"] == "doc-no-optional-strings"
    assert meta["url"] == "http://example.com/no-strings"

    # Optional strings should NOT be present at all
    assert "title" not in meta
    assert "thumb" not in meta
    assert "website" not in meta
    assert "publish_date" not in meta
    assert "first_publish_date" not in meta

def test_extract_metadata_uses_empty_arrays_for_missing_array_fields():
    """
    For array fields (sections, categories, tags), schema requires:
      - Use [] for missing array fields, not null.
    """
    raw = {
        "_id": "doc-no-arrays",
        "url": "http://example.com/no-arrays",
        "website": "example",
        # no sections/categories/tags at all
    }

    meta = extract_metadata(raw)

    assert "sections" in meta and meta["sections"] == []
    assert "categories" in meta and meta["categories"] == []
    assert "tags" in meta and meta["tags"] == []

def test_extract_metadata_preserves_array_fields():
    raw = {
        "_id": "doc-array-fields",
        "url": "http://example.com/arrays",
        "website": "example-site",
        "sections": ["News", "Local"],
        "categories": ["Category1", "Category2"],
        "tags": ["tag1", "tag2"],
    }

    meta = extract_metadata(raw)

    assert meta["external_id"] == "doc-array-fields"
    assert meta["url"] == "http://example.com/arrays"

    assert isinstance(meta["sections"], list)
    assert meta["sections"] == ["News", "Local"]

    assert isinstance(meta["categories"], list)
    assert meta["categories"] == ["Category1", "Category2"]

    assert isinstance(meta["tags"], list)
    assert meta["tags"] == ["tag1", "tag2"]

def test_extract_metadata_normalizes_missing_arrays_to_empty_lists():
    raw = {
        "_id": "doc-missing-arrays",
        "url": "http://example.com/no-arrays",
        "website": "example-site",
        # no sections / categories / tags keys at all
    }

    meta = extract_metadata(raw)

    assert meta["external_id"] == "doc-missing-arrays"
    assert meta["url"] == "http://example.com/no-arrays"

    # arrays must exist and be []
    assert "sections" in meta
    assert meta["sections"] == []

    assert "categories" in meta
    assert meta["categories"] == []

    assert "tags" in meta
    assert meta["tags"] == []

from src.capitol_pipeline.transformers import extract_metadata

def test_extract_metadata_preserves_valid_iso_date():
    """
    Valid ISO-8601 publish_date should be preserved as-is in metadata.
    """
    raw = {
        "_id": "doc-valid-date",
        "url": "http://example.com/valid-date",
        "additional_properties": {
            "publish_date": "2025-07-02T00:00:00Z",
        },
    }

    meta = extract_metadata(raw)

    assert meta["external_id"] == "doc-valid-date"
    assert meta["url"] == "http://example.com/valid-date"
    # Date preserved exactly
    assert meta["publish_date"] == "2025-07-02T00:00:00Z"
def test_extract_metadata_normalizes_millisecond_dates():
    """
    Dates with millisecond suffix `.000Z` should be normalized to `Z`.
    """
    raw = {
        "_id": "doc-ms-date",
        "url": "http://example.com/ms-date",
        "additional_properties": {
            "publish_date": "2025-07-02T00:00:00.000Z",
            "datetime": "2025-07-03T12:34:56.000Z",
            "first_publish_date": "2025-07-01T08:00:00.000Z",
        },
    }

    meta = extract_metadata(raw)

    assert meta["publish_date"] == "2025-07-02T00:00:00Z"
    assert meta["datetime"] == "2025-07-03T12:34:56Z"
    assert meta["first_publish_date"] == "2025-07-01T08:00:00Z"

def test_to_qdrant_format_returns_none_for_whitespace_only_text():
    raw = {
        "_id": "doc-whitespace-only",
        "title": "Whitespace only",
        "url": "http://example.com/whitespace-only",
        "website": "example",
        "content_elements": [
            {"type": "text", "content": "    "},
            {"type": "text", "content": "\n\t   "},
        ],
    }

    doc = to_qdrant_format(raw)
    assert doc is None



