# Submission Guidelines

Thank you for completing the Capitol AI coding assessment. This document provides clear guidance on what to submit and how.

## What to Submit

### 1. Code Repository

Provide your solution as either:
- **GitHub/GitLab repository** (preferred) - Include the URL in your submission email
- **Zip file** - Name it `capitol-ai-assessment-<your-name>.zip`

### 2. Required Files

Your submission must include:

#### README.md (Required)
Your README should contain:
- **Setup instructions**
  - Prerequisites (Python version, system requirements)
  - Installation steps (dependencies, virtual environment, etc.)
  - Configuration (environment variables, API keys, etc.)
- **How to run**
  - Commands to execute your solution
  - Expected output or results
  - How to verify it works correctly
- **Architecture overview**
  - High-level design and components
  - Key technology choices
- **Testing**
  - How to run tests
  - What is tested

#### Source Code (Required)
- All application code
- Tests (if you wrote them)
- Configuration files
- Dependency specifications (requirements.txt, pyproject.toml, etc.)

#### approach.md (Recommended)
A separate document discussing:
- **Your thought process**
  - Why you chose your focus area (Path A, B, or C)
  - How you approached the problem
- **Key decisions**
  - Technology and tool choices
  - Architectural decisions
  - Trade-offs you made
- **Limitations**
  - Known issues or edge cases not handled
  - What you would do differently with more time
  - Areas that could be improved
- **Challenges**
  - Interesting problems you solved
  - Technical difficulties you encountered

### 3. Optional Items

These are not required but can strengthen your submission:

- **Deployment artifacts**
  - Dockerfile
  - docker-compose.yml
  - Kubernetes manifests
  - Terraform/IaC files
- **CI/CD configuration**
  - GitHub Actions, GitLab CI, or similar
- **Architecture diagrams**
  - System design diagrams
  - Data flow diagrams
- **API documentation**
  - If you built an API
  - OpenAPI/Swagger specs
- **Performance benchmarks**
  - If you optimized for performance
  - Profiling results

### 4. Live Deployment (Extra Credit)

If you deployed your solution, include:
- **URL** to the deployed service
- **API documentation** (if applicable)
- **How to test it** (example requests, credentials if needed)
- **Infrastructure details** (where it's hosted, how it's deployed)

**Important**: If you deployed to a cloud service that costs money, you can tear it down after we review. Just include screenshots or recordings demonstrating it worked.

---

## Submission Checklist

Before submitting, verify:

- [ ] Code runs following the README instructions
- [ ] All dependencies are documented
- [ ] Environment variables and configuration are explained
- [ ] Tests pass (if you wrote tests)
- [ ] Output matches the Qdrant schema
- [ ] No sensitive information in the repository (API keys, passwords, etc.)
- [ ] README clearly explains setup and usage
- [ ] You've documented your design decisions
- [ ] You've been honest about limitations

---

## Submission Format Examples

### Good README Structure Example

```markdown
# Capitol AI Assessment - Data Ingestion Pipeline

## Overview
Brief description of your solution and approach.

## Prerequisites
- Python 3.11+
- OpenAI API key (for embeddings)
- Docker (optional, for Qdrant)

## Installation

\`\`\`bash
# Clone and setup
git clone <your-repo>
cd capitol-ai-assessment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
\`\`\`

## Configuration

Create a `.env` file:
\`\`\`
OPENAI_API_KEY=your_key_here
QDRANT_URL=http://localhost:6333
\`\`\`

## Usage

\`\`\`bash
# Run transformation
python src/main.py --input data/raw_customer_api.json --output transformed.json

# Run tests
pytest tests/
\`\`\`

## Architecture

Brief description of your design...

## Design Decisions

- Why I chose OpenAI for embeddings: ...
- How I handled missing fields: ...
- Trade-offs in text extraction: ...

## Testing

Run test suite:
\`\`\`bash
pytest tests/ -v
\`\`\`

Coverage: 85% (see coverage/index.html)

## Known Limitations

- Only handles up to 10K documents efficiently
- HTML stripping is basic (doesn't handle all edge cases)
- No retry logic for embedding API failures

## Future Improvements

Given more time, I would:
- Add async processing for performance
- Implement proper HTML parsing with BeautifulSoup
- Add retry logic with exponential backoff
```

---

## Common Mistakes to Avoid

### ❌ Don't Do This

1. **Incomplete setup instructions**
   ```
   # Bad
   Just run main.py
   ```
   What Python version? What dependencies? What configuration?

2. **Hardcoded paths or credentials**
   ```python
   # Bad
   API_KEY = "sk-abc123..."
   file = open("/Users/yourname/Downloads/data.json")
   ```

3. **No error handling explanation**
   ```python
   # Bad - crashes without explanation
   data = json.loads(response)['content'][0]['text']
   ```

4. **Undocumented assumptions**
   - Assuming certain data exists
   - Assuming specific Python version
   - Assuming specific environment

5. **No explanation of what doesn't work**
   - Claiming everything works when it doesn't
   - Not documenting known issues

### ✅ Do This Instead

1. **Clear, complete setup**
   ```markdown
   ## Prerequisites
   - Python 3.11 or higher
   - 2GB RAM minimum
   - OpenAI API key

   ## Installation
   [Step by step instructions with expected output]
   ```

2. **Configuration management**
   ```python
   # Good
   from os import getenv
   API_KEY = getenv("OPENAI_API_KEY")
   if not API_KEY:
       raise ValueError("OPENAI_API_KEY environment variable required")
   ```

3. **Defensive coding with explanation**
   ```python
   # Good - handles missing data
   try:
       text = data['content'][0]['text']
   except (KeyError, IndexError) as e:
       logger.warning(f"Missing text content: {e}")
       text = ""  # Use empty string as fallback
   ```

4. **Document decisions**
   ```markdown
   ## Design Decisions

   ### Text Extraction
   I chose to concatenate all text elements and strip HTML tags because...
   Trade-off: This loses formatting but ensures clean text for embeddings.
   ```

5. **Be honest about limitations**
   ```markdown
   ## Known Limitations
   - HTML stripping is basic (doesn't handle nested tags well)
   - No handling for very long documents (>10K tokens)
   - Would need optimization for 1000+ document batches
   ```

---

## Environment Variables and Secrets

### Never Commit

- ❌ API keys
- ❌ Passwords
- ❌ Private keys
- ❌ Tokens

### Instead

1. Use `.env` file (add to `.gitignore`)
2. Provide `.env.example` with dummy values
3. Document required environment variables in README

Example `.env.example`:
```bash
# OpenAI Configuration
OPENAI_API_KEY=sk-your-key-here

# Qdrant Configuration
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=optional-if-using-cloud

# Application Configuration
LOG_LEVEL=INFO
BATCH_SIZE=10
```

---

## How to Submit

Send your submission to your recruiting contact with:

**Subject**: Capitol AI Assessment Submission - [Your Name]

**Email should include**:
- Link to your repository (if using GitHub/GitLab)
- OR attachment of zip file
- Brief summary (2-3 sentences) of your approach
- Approximate time spent (optional but helpful)
- Any special instructions or notes

**Example email**:

```
Subject: Capitol AI Assessment Submission - Jane Smith

Hi [Recruiter Name],

I've completed the Capitol AI coding assessment. Here's my submission:

Repository: https://github.com/janesmith/capitol-ai-assessment
Deployed URL: https://my-ingestion-api.com (optional)

I focused on building a robust data transformation pipeline with
comprehensive error handling and test coverage (Path A). I transformed
all 50 documents and achieved 90% test coverage.

Time spent: ~8 hours

Please let me know if you have any questions or need clarification
on any aspects of my solution.

Best regards,
Jane Smith
```

---

## Timeline

- We aim to review submissions within 5-7 business days
- You'll receive feedback regardless of outcome
- If we proceed, next step is a technical interview with the team

---

## Questions?

If you have questions about submission:
- Email your recruiting contact
- We respond within 24 hours on business days

---

## After Submission

### What Happens Next

1. **Initial Review** (2-3 days)
   - We verify your solution runs
   - Initial code review
   - Functional testing

2. **Detailed Evaluation** (3-5 days)
   - Complete rubric evaluation
   - Team discussion
   - Decision on next steps

3. **Feedback** (Within 7 days)
   - You'll hear from us either way
   - If proceeding: Schedule technical interview
   - If not proceeding: We provide constructive feedback

### What We're Looking For

Remember, we're evaluating:
- Can you write production-quality code?
- Do you make good engineering decisions?
- Can you handle ambiguity and complexity?
- Would we want you on our team?

Your assessment is reviewed by multiple team members who will be your potential colleagues.

---

Thank you for your interest in Capitol AI. We look forward to reviewing your submission!
