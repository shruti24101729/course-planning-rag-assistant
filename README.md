# Course Planning RAG Assistant

 
Agentic RAG Challenge: Prerequisite & Course Planning Assistant (Catalog-Grounded)

---

## Overview

A **4-stage LangChain RAG pipeline** that answers student course-planning questions strictly grounded in MIT's Course 6-3 (Computer Science and Engineering) academic catalog. Every prerequisite claim, program requirement, and academic policy response is backed by verifiable citations from the source documents.

### Key Features

| Capability | Implementation |
|---|---|
| Grounded answers with citations | Every response cites `[source_file § section (chunk_id) \| URL]` |
| Prerequisite chain reasoning | Multi-query retrieval + structured Decision/Evidence/Next-Step output |
| Course plan generation | Profile-driven planner with justification per course |
| Clarifying questions | Intake stage identifies missing profile fields (max 5 Qs) |
| Safe abstention | Verifier blocks unsupported claims; "not in docs" returns guidance |

---

## Architecture

```
User Input
    │
    ▼
┌─────────────────┐
│  Stage 1: INTAKE │  ← Normalize student profile; ask clarifying Qs if needed
└────────┬────────┘
         │ Structured profile JSON
         ▼
┌──────────────────────┐
│ Stage 2: RETRIEVAL   │  ← Multi-query FAISS search (k=6, cosine ≥ 0.15)
│ (multi-query)        │    Deduplicates by chunk_id
└────────┬─────────────┘
         │ Retrieved chunks + citation strings
         ▼
┌──────────────────────────────────┐
│ Stage 3: PLANNER / PREREQ CHECK  │  ← GPT-4o with citation-enforcing prompt
│ (grounded generation)            │    Structured output template
└────────┬─────────────────────────┘
         │ Draft response
         ▼
┌────────────────────────┐
│ Stage 4: VERIFIER      │  ← Audits citations; flags unsupported claims
│ (citation auditor)     │    Forces revision if needed (NEEDS_REVISION path)
└────────┬───────────────┘
         │ Final verified response
         ▼
    Output to user
```

### RAG Pipeline Details

| Component | Choice | Rationale |
|---|---|---|
| Embeddings | `text-embedding-3-small` | High quality, cost-efficient for catalog text |
| Vector Store | FAISS (cosine) | Fast, no server needed, easy to persist |
| Chunk size | 600 tokens | Captures full course entries + surrounding context |
| Chunk overlap | 100 tokens | Prevents prerequisite lists from being split at boundaries |
| Retrieval k | 6 chunks | Balances recall vs. GPT-4o context window |
| Score threshold | 0.25 cosine | Filters out irrelevant chunks before generation |
| LLM | GPT-4o, temp=0 | Deterministic; best instruction-following for citation enforcement |

---

## Data Sources (Catalog)

All documents are in `data/catalog/`. Total: ~30,000+ words across 3 source files.

| File | Source URL | Date Accessed | Coverage |
|---|---|---|---|
| `mit_cs_courses.txt` | https://student.mit.edu/catalog/m6a.html | 2026-03-27 | 24 course entries: 6.009, 6.004, 6.006, 6.031, 6.033, 6.034, 6.035, 6.036, 6.041, 6.042J, 6.046J, 6.814, 6.824, 6.829, 6.830, 6.854J, 6.858, 6.867, 6.UAT, 6.UAP, 18.01, 18.02, 18.06, 18.600, 18.650 |
| `mit_6_3_requirements.txt` | https://www.eecs.mit.edu/academics/undergraduate-programs/curriculum/6-3-computer-science-and-engineering/ | 2026-03-27 | Full 6-3 degree requirements: Foundations, Headers, AUS categories, GIR, credit minimums, GPA rules, double-counting rules, sample 4-year plan |
| `mit_academic_policies.txt` | https://registrar.mit.edu/registration-academics/academic-policies-procedures | 2026-03-27 | Grading (P/F, P/NR, Incomplete), enrollment limits, add/drop deadlines, repeat policy, transfer credit, AP credit, prerequisite override/instructor consent, co-requisites, leave of absence |

---

## Setup

### 1. Prerequisites

- Python 3.11+
- OpenAI API key

### 2. Install

```bash
git clone https://github.com/shruti24101729/course-planning-rag.git
cd course-planning-rag
pip install -r requirements.txt
```

### 3. Configure API key

```bash
export OPENAI_API_KEY="sk-..."
# Or create a .env file:
echo "OPENAI_API_KEY=sk-..." > .env
```

### 4. Build the FAISS index

```bash
python main.py --build-index
```

This reads `data/catalog/*.txt`, chunks them, embeds with OpenAI, and saves the FAISS index to `faiss_index/`.

---

## Running

### Sample Interactions (3 required transcripts)

```bash
python main.py --demo
```

Runs 3 transcripts:
1. Prereq eligibility check with citations
2. Course plan generation with justification
3. Safe abstention for out-of-catalog question

### Full Evaluation (25 queries)

```bash
python main.py --eval
```

Outputs metrics to console and saves `evaluation/eval_results.json`.

### Interactive Mode

```bash
python main.py --interactive
```

### Direct API usage

```python
from src.chain import CoursePlanningAssistant

assistant = CoursePlanningAssistant()

# Prerequisite check
result = assistant.run_prereq_check(
    completed_courses=["6.009", "6.042J"],
    grades={"6.009": "A", "6.042J": "B"},
    question="Can I take 6.006?",
)
print(result["response"])

# Course plan
result = assistant.run(
    "I completed 6.009(A), 6.042J(B), 18.01(A), 18.02(B), 6.004(B). "
    "Plan my Fall 2026 semester. Max 48 units. Major: 6-3. Catalog: 2025-2026."
)
print(result["response"])
```

---

## Output Format

Every response follows:

```
ANSWER / PLAN:
<summary>

SUGGESTED COURSES (for plans) or DECISION/EVIDENCE/REASONING (for prereq checks):
  Course: <number>
  Justification: ...
  Prerequisite Check:
    Decision: Eligible / Not Eligible / Need More Info
    Evidence: [citation]
    Next Step: ...

CITATIONS:
- [source_file § section (chunk_id) | URL]

CLARIFYING QUESTIONS (if needed):
  1. ...

RISKS / ASSUMPTIONS:
  - ...
```

---

## Evaluation Results

Run `python main.py --eval` to reproduce. Expected targets:

| Metric | Target | Description |
|---|---|---|
| Citation coverage | ≥ 85% | % of responses with at least 1 citation |
| Eligibility correctness | ≥ 80% | % of A+B queries with correct decision |
| Abstention accuracy | 100% | % of D queries that correctly abstain |

---

## Project Structure

```
course-planning-rag/
├── main.py                     # Entry point (--demo, --eval, --interactive)
├── app.py  
├── requirements.txt
├── README.md
├── src/
│   ├── ingest.py                # Document loading, chunking, FAISS index building
│   ├── retriever.py             # Retriever config, citation formatting
│   ├── prompts.py               # All LLM prompt templates (4 stages)
│   └── chain.py                 # Pipeline orchestration
├── data/
│   └── catalog/
│       ├── mit_cs_courses.txt           # 24 course entries
│       ├── mit_6_3_requirements.txt     # Degree requirements
│       └── mit_academic_policies.txt    # Academic policies
├── evaluation/
│   ├── eval_queries.py          # 25-query test set + runner
│   └── eval_results.json        # Output from --eval run
└── faiss_index/                 # Auto-generated; gitignored
    ├── index.faiss
    └── index.pkl
```

---

## Failure Modes and Next Steps

**Known limitations:**
- Availability data (which term a course actually runs) is not in the catalog → correctly abstained
- Instructor-specific decisions (will Prof. X waive a prereq?) cannot be answered → correctly abstained
- Grade-threshold nuance: some instructors set higher minimums than the catalog default; system notes this caveat

**Improvements for v2:**
1. Add semester-specific Schedule of Classes scraping (live availability)
2. Hybrid retrieval (BM25 + dense) for better recall on course-code exact matches
3. Re-ranking (cross-encoder) before generation for higher precision
4. Persistent conversation history for multi-turn planning sessions

