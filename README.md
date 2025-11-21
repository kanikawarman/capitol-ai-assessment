# Capitol AI - Data Ingestion Pipeline Assessment

## Overview

Welcome to the Capitol AI engineering assessment. Your task is to build a data ingestion pipeline that transforms customer API data into our internal document format and prepares it for vector database storage.

This assessment reflects real work we do at Capitol AI: integrating with diverse customer APIs, normalizing their data into our platform's format, and making it searchable through vector embeddings.

## The Challenge

You'll work with real customer API data - a content management system (CMS) that publishes news articles. Your goal is to transform this nested, complex API response into our clean, standardized Qdrant document format.

### What You'll Find in This Repository

```
data/
├── raw_customer_api.json       # Full dataset: 50 documents from customer API
├── raw_sample.json             # Quick iteration sample: 3 documents
├── qdrant_format_example.json  # Target format: 10 example documents
└── qdrant_schema.md            # Schema specification and requirements
```

## Requirements

### Core Requirements (Everyone Must Complete)

1. **Data Transformation**
   - Transform at least 10 documents from `raw_customer_api.json` to match the Qdrant schema
   - Your output must conform to the schema defined in `data/qdrant_schema.md`
   - Handle missing fields and edge cases gracefully

2. **Text Extraction**
   - Extract meaningful text content from the nested `content_elements` array
   - Strip HTML tags appropriately
   - Concatenate text segments into a single readable text field

3. **Metadata Extraction**
   - Map customer API fields to our metadata schema
   - Extract: title, url, external_id, dates, sections, categories, tags, thumbnail
   - Handle variations and missing fields

4. **Embeddings**
   - Generate vector embeddings for each document's text
   - Use any embedding model you prefer (OpenAI, Sentence Transformers, Cohere, etc.)
   - Document your model choice and dimension in your README

5. **Documentation**
   - Clear README with setup and run instructions
   - Document your design decisions and trade-offs
   - Explain how to verify your solution works

### Choose Your Focus

You can demonstrate your strengths by choosing to emphasize different aspects of the solution. We value depth over breadth.

#### Path A: Data Engineering Depth
Focus on robust, production-grade data transformation:
- ✅ Transform all 50 documents with comprehensive error handling
- ✅ Handle all edge cases (missing fields, malformed data, HTML entities, etc.)
- ✅ Extensive test coverage for transformation logic
- ✅ Data quality validation and reporting
- ✅ Idempotent processing (safe to re-run)

#### Path B: Infrastructure & Deployment
Focus on production-ready system architecture:
- ✅ Build a deployable ingestion API (REST or async job processor)
- ✅ Containerization (Docker) with deployment configuration
- ✅ Infrastructure as Code (Terraform, K8s manifests, or similar)
- ✅ Observability (structured logging, metrics, health checks)
- ✅ CI/CD considerations
- ✅ Vector database integration (any: Qdrant, Chroma, Weaviate, etc.)

#### Path C: Full-Stack Excellence
If you're fast and want to showcase comprehensive skills:
- ✅ Combine both paths above
- ✅ Demonstrate end-to-end working system

**Note**: There's no "correct" path. We're evaluating your engineering judgment, code quality, and ability to deliver production-ready solutions. Choose the path that best demonstrates your strengths for the role.

## Extra Credit Opportunities

These are explicitly called out as differentiators. Pick what interests you:

- ⭐ **Live Deployment**: Deploy your solution and provide a working URL
- ⭐ **Performance Optimization**: Async/batch processing, parallelization, streaming
- ⭐ **Error Recovery**: Dead letter queue, retry logic, circuit breakers
- ⭐ **Monitoring**: Metrics dashboards, distributed tracing, alerting
- ⭐ **Schema Evolution**: Handle multiple versions of the customer API format
- ⭐ **Testing Excellence**: Integration tests, contract tests, property-based tests
- ⭐ **Documentation**: API documentation, architecture diagrams, runbooks

## Technical Considerations

### Data Transformation Challenges

The customer API response is deeply nested with:
- Content split across multiple `content_elements` (text, images, HTML widgets)
- Complex taxonomy structure (sections, tags, categories spread across the document)
- Multi-website syndication (same article appears on multiple sites)
- Rich metadata (dates, credits, planning info, promo items)
- HTML content that needs cleaning

You'll need to decide:
- How to extract and concatenate text from `content_elements`
- What to do with HTML tags in content
- How to handle missing or null fields
- How to flatten the taxonomy structure
- Whether to convert relative URLs to absolute
- How to deal with duplicate/redundant metadata

### Embedding Generation

- You'll need an embedding service (OpenAI, Hugging Face, Cohere, etc.)
- Consider costs (OpenAI charges per token)
- Consider performance (sentence-transformers is free but slower)
- Document your choice and trade-offs

### Vector Database

- Any vector DB is acceptable: Qdrant, Chroma, Weaviate, Pinecone, etc.
- You can use local Docker instances for development
- You can mock the storage layer if focusing on transformation
- Document your choice and why

## Evaluation Criteria

We will evaluate your submission on:

### 1. Code Quality (40%)
- Clean, readable, well-structured code
- Appropriate design patterns and abstractions
- Error handling and edge case management
- Pythonic idioms and best practices

### 2. Functionality (30%)
- Correctness of the transformation logic
- Data quality of the output
- Handling of edge cases and errors
- System works as documented

### 3. Architecture & Design (20%)
- System design decisions and trade-offs
- Scalability and performance considerations
- Production-readiness thinking
- Appropriate use of tools and technologies

### 4. Communication (10%)
- Clear documentation and setup instructions
- Explanation of design decisions
- Honest discussion of limitations and trade-offs
- Professional presentation

**Note**: Your solution will be evaluated against our internal test suite that covers additional edge cases and integration scenarios beyond what you test for.

## Submission Guidelines

### What to Submit

1. **Your Code Repository**
   - Can be GitHub, GitLab, or a zip file
   - Include all source code, tests, and configuration

2. **README.md** with:
   - Setup instructions (dependencies, environment variables, etc.)
   - How to run your solution
   - How to verify it works (test commands, example output)
   - Architecture overview
   - Key design decisions

3. **approach.md** (recommended) with:
   - Your thought process and decision-making
   - Trade-offs you considered
   - What you would do differently with more time
   - Known limitations or areas for improvement

4. **Working Solution**
   - Must be runnable by following your README
   - Must produce valid output matching the schema
   - Tests should pass (if included)

5. **(Optional)** Deployed URL
   - If you deployed your solution, include the URL and API documentation

### What We're NOT Looking For

- ❌ Over-engineering for hypothetical future requirements
- ❌ Copying boilerplate without understanding it
- ❌ Incomplete solutions without acknowledgment of what's missing
- ❌ Lack of error handling or input validation
- ❌ Undocumented or unclear setup process

## Getting Started

1. **Explore the data**
   ```bash
   # Look at the raw customer API format
   cat data/raw_sample.json | jq '.[0]' | less

   # Look at the target format
   cat data/qdrant_format_example.json | jq '.[0]'

   # Read the schema specification
   cat data/qdrant_schema.md
   ```

2. **Start small**
   - Begin with `raw_sample.json` (just 3 documents)
   - Get the transformation working for one document
   - Handle edge cases as you discover them
   - Expand to the full dataset

3. **Iterate**
   - Start with a simple working solution
   - Add error handling and tests
   - Optimize and refine
   - Add infrastructure/deployment if that's your focus

4. **Document as you go**
   - Write your README with setup instructions
   - Note design decisions and trade-offs
   - Be honest about limitations

## Questions?

We value candidates who ask clarifying questions and communicate well. If you need clarification on:
- Requirements or expectations
- Schema specifications or edge cases
- Technical constraints or infrastructure

Please reach out to your recruiting contact. We're happy to help ensure you can put your best work forward.

## Tips for Success

- **Focus on quality over quantity**: A well-done subset is better than a rushed complete solution
- **Show your thinking**: We care about your engineering judgment and decision-making
- **Be pragmatic**: Production-ready doesn't mean perfect - document trade-offs
- **Choose your battles**: You can't do everything - prioritize what matters
- **Test your setup instructions**: Can someone else run your code?

Good luck! We're excited to see your solution.

---

## About Capitol AI

Capitol AI builds AI-powered document generation and research platforms. We work with complex data ingestion pipelines, vector databases, LLM orchestration, and multi-tenant microservices. This assessment reflects the kind of work our engineers do daily: integrating diverse data sources into our unified platform.

Learn more at [capitol.ai](https://capitol.ai)
