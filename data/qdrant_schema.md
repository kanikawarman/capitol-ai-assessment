# Qdrant Document Schema Specification

This document describes the expected format for documents that will be ingested into our Qdrant vector database.

## Schema Overview

Each document must be a JSON object with the following structure:

```json
{
  "text": "Full text content of the document...",
  "metadata": {
    "title": "Document title",
    "url": "https://example.com/article",
    "external_id": "UNIQUE_ID",
    "publish_date": "2025-07-02T00:00:00Z",
    "datetime": "2025-07-02T00:00:00Z",
    "first_publish_date": "2025-07-02T00:00:00Z",
    "website": "sitename",
    "sections": ["Section1", "Section2"],
    "categories": ["Category1", "Category2"],
    "tags": ["tag1", "tag2"],
    "thumb": "https://example.com/image.jpg"
  }
}
```

## Field Specifications

### Required Fields

#### `text` (string, required)
- The full text content of the document
- Should contain all readable text from the article/document
- HTML tags should be stripped or converted to plain text
- Empty strings are not allowed

#### `metadata` (object, required)
Container for all document metadata

#### `metadata.external_id` (string, required)
- Unique identifier from the source system
- Must be globally unique across all documents
- Used for deduplication and updates

#### `metadata.url` (string, required)
- Canonical URL for the document
- Should be a valid URL (absolute or relative path)

### Optional Fields

#### `metadata.title` (string, optional)
- Human-readable title of the document
- Recommended to include when available

#### `metadata.publish_date` (string, optional)
- ISO 8601 formatted timestamp
- Format: `YYYY-MM-DDTHH:MM:SSZ`

#### `metadata.datetime` (string, optional)
- ISO 8601 formatted timestamp
- Typically the same as publish_date but may represent different semantics

#### `metadata.first_publish_date` (string, optional)
- ISO 8601 formatted timestamp
- Original publication date (may differ from current publish_date if republished)

#### `metadata.website` (string, optional)
- Website identifier/slug
- Example: "nj", "lehighvalleylive"

#### `metadata.sections` (array of strings, optional)
- List of section names the document belongs to
- Example: ["News", "Sports"]

#### `metadata.categories` (array of strings, optional)
- List of category names for content classification
- Can be empty array if no categories

#### `metadata.tags` (array of strings, optional)
- List of tags associated with the document
- Can be empty array if no tags

#### `metadata.thumb` (string, optional)
- URL to thumbnail/preview image
- Should be a valid URL

## Data Quality Guidelines

1. **Text Extraction**: Extract all meaningful text from the source document. This typically involves:
   - Concatenating text from multiple content elements
   - Stripping HTML tags while preserving readability
   - Removing navigation elements, ads, and other non-content text

2. **Metadata Completeness**: Include as many metadata fields as available from the source
   - Don't fabricate missing data
   - Use empty arrays for missing array fields (not null)
   - Omit optional string fields if not available (don't use empty strings)

3. **Date Formatting**: All dates must be ISO 8601 compliant
   - Use UTC timezone (Z suffix)
   - Format: `YYYY-MM-DDTHH:MM:SSZ`

4. **URL Handling**:
   - Convert relative URLs to absolute URLs when possible
   - Ensure URLs are properly formatted

## Example Transformations

See `qdrant_format_example.json` for real examples of properly formatted documents.

### Minimal Valid Document
```json
{
  "text": "This is the document content.",
  "metadata": {
    "external_id": "doc123",
    "url": "/path/to/document"
  }
}
```

### Fully Populated Document
```json
{
  "text": "Full article text here...",
  "metadata": {
    "title": "Breaking News: Important Event",
    "url": "https://example.com/news/breaking-story",
    "external_id": "ABC123XYZ",
    "publish_date": "2025-07-02T14:30:00Z",
    "datetime": "2025-07-02T14:30:00Z",
    "first_publish_date": "2025-07-02T14:00:00Z",
    "website": "example",
    "sections": ["News", "Politics"],
    "categories": ["Government", "Elections"],
    "tags": ["breaking", "election2025", "politics"],
    "thumb": "https://example.com/images/story-thumbnail.jpg"
  }
}
```

## Edge Cases to Handle

1. **Missing or Null Fields**: Handle gracefully, omit from output
2. **Empty Arrays**: Use `[]` not `null`
3. **HTML in Text**: Strip tags, decode entities
4. **Invalid Dates**: Handle malformed date strings
5. **Duplicate External IDs**: Should not occur, but detect and handle
6. **Very Long Text**: No length limit specified, but consider truncation if needed for embedding generation

## Vector Embedding Requirements

While not part of the document schema itself, documents will be processed to generate vector embeddings:

- **Embedding Model**: Use any embedding model of your choice (OpenAI, Sentence Transformers, Cohere, etc.)
- **Dimension**: Document your chosen model's dimension in your README
- **Text to Embed**: Use the `text` field as the source for embedding generation

The embedding itself does not need to be included in this JSON schema - it will be generated during ingestion and stored separately in the vector database.
