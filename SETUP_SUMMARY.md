# Capitol AI Assessment V2 - Setup Complete ✓

## What's Been Created

Your new hybrid coding assessment is ready at:
```
~/dev/cap/capitol-ai-assessment-v2/
```

### Public Files (Share with Candidates)

1. **README.md** - Main assessment instructions
   - Overview and challenge description
   - Three focus paths (Data Engineering, Infrastructure, Full-Stack)
   - Core requirements and extra credit opportunities
   - Evaluation criteria overview
   - No time guidance (intentionally)

2. **SUBMISSION.md** - Submission guidelines
   - What to submit and how
   - Checklist and examples
   - Common mistakes to avoid
   - Email template for submission

3. **data/** directory:
   - `raw_customer_api.json` - 50 real CMS documents from customer API
   - `raw_sample.json` - 3 documents for quick iteration
   - `qdrant_format_example.json` - 10 transformed examples (target format)
   - `qdrant_schema.md` - Detailed schema specification

### Internal Files (DO NOT Share with Candidates)

4. **EVALUATION_RUBRIC.md** - Detailed scoring rubric
   - 100 point scoring framework (Code Quality 40, Functionality 30, Architecture 20, Communication 10)
   - Up to 20 bonus points for exceptional work
   - Specific scoring criteria for each category
   - Path-specific evaluation guidance
   - Red flags and calibration examples

5. **INTERNAL_README.md** - Team documentation
   - How to send the assessment to candidates
   - Evaluation process (step-by-step)
   - Reviewer FAQ
   - Calibration guidelines
   - Maintenance notes

6. **.gitignore** - Excludes internal files from public repo

---

## Next Steps

### 1. Review the Assessment (Recommended)

Read through these files in order:
1. `README.md` - See what candidates will see
2. `data/qdrant_schema.md` - Understand the schema they need to produce
3. `EVALUATION_RUBRIC.md` - Review scoring criteria
4. Browse the data files to understand the transformation challenge

### 2. Test the Data Files

Verify the data files are correct:
```bash
cd ~/dev/cap/capitol-ai-assessment-v2

# Check file sizes
ls -lh data/

# View sample data
cat data/raw_sample.json | jq '.[0]' | head -50
cat data/qdrant_format_example.json | jq '.[0]'

# Verify document counts
cat data/raw_customer_api.json | jq 'length'  # Should be 50
cat data/raw_sample.json | jq 'length'        # Should be 3
cat data/qdrant_format_example.json | jq 'length'  # Should be 10
```

### 3. Decide on Distribution Method

**Option A: Private GitHub Repository** (Recommended)
```bash
cd ~/dev/cap/capitol-ai-assessment-v2
git init
git add README.md SUBMISSION.md data/ .gitignore
git commit -m "Initial assessment v2"
# Create private repo on GitHub
git remote add origin <your-repo-url>
git push -u origin main
```

**Option B: Zip File Distribution**
```bash
cd ~/dev/cap
zip -r capitol-ai-assessment-v2-public.zip \
  capitol-ai-assessment-v2/README.md \
  capitol-ai-assessment-v2/SUBMISSION.md \
  capitol-ai-assessment-v2/data \
  capitol-ai-assessment-v2/.gitignore
```

### 4. Setup Internal Repo (Recommended)

Keep evaluation materials separate:
```bash
# Option: Create separate internal repo
cd ~/dev/cap
mkdir capitol-ai-assessment-v2-internal
cp capitol-ai-assessment-v2/EVALUATION_RUBRIC.md capitol-ai-assessment-v2-internal/
cp capitol-ai-assessment-v2/INTERNAL_README.md capitol-ai-assessment-v2-internal/
# Initialize as private Git repo
```

### 5. Pilot Test (Highly Recommended)

Before sending to real candidates:
1. Have 1-2 engineers on your team complete it
2. Time them and get feedback
3. Verify setup instructions are clear
4. Calibrate scoring rubric
5. Adjust based on feedback

### 6. Create Email Template

Prepare a candidate email template (suggested in INTERNAL_README.md):
```
Subject: Capitol AI - Coding Assessment

Hi [Candidate Name],

Thanks for your continued interest in the Senior Full-Stack Engineer role.

The next step is a take-home coding assessment. This reflects real work we do:
transforming customer API data into our vector database format.

Assessment repository: [Link or attachment]

Key points:
- Open-ended assessment - no single right answer
- Choose your focus: data engineering OR infrastructure OR both
- We value quality over quantity
- Submit within 7 days

All instructions are in the README.md. Questions? Just ask.

Looking forward to your solution!

Best,
[Your Name]
```

---

## What Makes This Assessment Work

### 1. Realistic Work Sample
- Real customer API data (messy, nested CMS structure)
- Actual transformation challenge you face with qdrant-svc
- Tests skills they'll use on the job

### 2. Hybrid Approach
- Candidates choose their focus area
- Data engineering depth OR infrastructure/deployment OR both
- Reveals strengths without penalizing for not doing everything

### 3. No Time Pressure
- No stated time limit
- Candidates work at their own pace
- Tests judgment of when "done" is good enough

### 4. Clear Evaluation
- Objective 100-point rubric
- Specific criteria for each score level
- Bonus points for exceptional work
- Reduces bias and increases consistency

### 5. Real Embeddings Required
- Not mocked - tests their ability to integrate with APIs
- Their choice of provider (tests decision-making)
- Realistic cost/performance trade-offs

### 6. Flexible Storage
- Any vector DB or mocked storage
- Tests architectural thinking
- Doesn't require specific tool knowledge

---

## Quick Start Checklist

- [ ] Review README.md (candidate view)
- [ ] Review EVALUATION_RUBRIC.md (team view)
- [ ] Verify data files are correct
- [ ] Decide: GitHub repo or zip distribution
- [ ] Setup internal evaluation repo
- [ ] Pilot test with 1-2 team members
- [ ] Create email template
- [ ] Brief the team on evaluation process
- [ ] Send to first real candidate

---

## Customization Options

If you want to adjust before using:

### Make It Easier
- Provide a basic project skeleton (pyproject.toml, basic structure)
- Give them a Dockerfile template
- Reduce required documents from 10 to 5

### Make It Harder
- Require all 50 documents transformed
- Require deployment (not optional)
- Add a time constraint
- Require specific vector DB (Qdrant)

### Change Focus
- Emphasize testing more (require 80% coverage)
- Emphasize infrastructure more (require K8s)
- Add a second data source to transform

**Recommendation**: Start with current version, calibrate after 3-5 candidates, then adjust.

---

## Troubleshooting

### If Data Files Don't Look Right

Check the source files:
```bash
# Verify source files exist
ls -lh /Users/admin/Downloads/response_1763707753294.json
ls -lh /Users/admin/dev/cap/qdrant-svc/src/openapi_examples/advance_local_docs.json

# Recreate if needed
cd ~/dev/cap/capitol-ai-assessment-v2
cat /Users/admin/Downloads/response_1763707753294.json | jq '.[0:3]' > data/raw_sample.json
```

### If You Need to Update Schema

Edit `data/qdrant_schema.md` with your actual Qdrant document requirements.

### If You Want Different Sample Size

```bash
# Create 5 document sample instead of 3
cat data/raw_customer_api.json | jq '.[0:5]' > data/raw_sample.json

# Create 20 example transformations instead of 10
cat /Users/admin/dev/cap/qdrant-svc/src/openapi_examples/advance_local_docs.json | jq '.[0:20]' > data/qdrant_format_example.json
```

---

## Success Metrics

After using this assessment, track:

1. **Completion Rate**
   - What % of candidates complete it?
   - Target: >80% completion

2. **Time Investment**
   - How long do candidates spend?
   - Track in submission emails

3. **Predictive Value**
   - Do high scorers perform well on the job?
   - Calibrate rubric based on actual performance

4. **Candidate Feedback**
   - Do candidates find it fair and relevant?
   - Adjust based on feedback

---

## Support

Questions or issues:
- Review INTERNAL_README.md for detailed guidance
- Consult EVALUATION_RUBRIC.md for scoring questions
- Calibrate with team after first few uses

---

## Version Info

- **Created**: 2025-01-21
- **Version**: 2.0
- **Replaces**: Old RAG/Q&A assessment
- **Based on**: Real qdrant-svc ingestion pipeline work

---

Good luck with your hiring! This assessment should give you much better signal on candidates' real-world abilities.
