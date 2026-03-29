"""
chain.py — 4-stage LangChain pipeline for the Course Planning Assistant.

Pipeline stages:
  1. IntakeChain    — normalize student profile, identify missing fields
                      (skipped for simple factual/availability questions)
  2. RetrieverChain — multi-query retrieval for prerequisites + program requirements
  3. PlannerChain   — generate grounded course plan or answer prereq question
  4. VerifierChain  — audit citations, flag unsupported claims, optionally rewrite
"""

import json
import re
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain_core.output_parsers import StrOutputParser

from src.ingest import get_or_build_index
from src.retriever import build_retriever, retrieve_with_citations, format_context
from src.prompts import (
    INTAKE_SYSTEM_PROMPT, INTAKE_HUMAN_TEMPLATE,
    PLANNER_SYSTEM_PROMPT, PLANNER_HUMAN_TEMPLATE,
    PREREQ_CHECK_SYSTEM_PROMPT, PREREQ_CHECK_HUMAN_TEMPLATE,
    VERIFIER_SYSTEM_PROMPT, VERIFIER_HUMAN_TEMPLATE,
)

# ---------------------------------------------------------------------------
# LLM configuration
# ---------------------------------------------------------------------------
LLM_MODEL       = "gpt-4o"
LLM_TEMPERATURE = 0.0   # deterministic for grounded factual tasks


def _build_llm(temperature: float = LLM_TEMPERATURE) -> ChatOpenAI:
    return ChatOpenAI(model=LLM_MODEL, temperature=temperature)


def _build_chain(system_prompt: str, human_template: str):
    """Build a simple prompt -> LLM -> string output chain."""
    prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(system_prompt),
        HumanMessagePromptTemplate.from_template(human_template),
    ])
    return prompt | _build_llm() | StrOutputParser()


# ---------------------------------------------------------------------------
# Helper — question type detection
# ---------------------------------------------------------------------------

def _is_prereq_question(text: str) -> bool:
    """Detect prerequisite eligibility questions."""
    keywords = [
        "can i take", "eligible", "prerequisite", "prereq",
        "am i allowed", "what do i need", "co-requisite",
        "have i completed", "do i qualify", "can i enroll",
    ]
    lower = text.lower()
    return any(k in lower for k in keywords)


def _is_factual_question(text: str) -> bool:
    """
    Detect simple factual or availability questions that do NOT need
    a student profile — these skip the Intake stage entirely.
    """
    keywords = [
        "who is", "who teaches", "professor", "instructor",
        "is it offered", "being offered", "offered in",
        "available in", "how many seats", "when is",
        "what time", "internship", "count as credit",
        "average gpa", "seats left", "section times",
        "definitely being offered", "what semester",
    ]
    lower = text.lower()
    return any(k in lower for k in keywords)


# ---------------------------------------------------------------------------
# Helper — extract profile from Intake output
# ---------------------------------------------------------------------------

def _extract_profile(text: str) -> str:
    """
    Parse PROFILE_COMPLETE: plain-text block or PROFILE_JSON: JSON block
    and return a JSON string for downstream stages.
    """
    marker = None
    if "PROFILE_COMPLETE:" in text:
        marker = "PROFILE_COMPLETE:"
    elif "PROFILE_JSON:" in text:
        marker = "PROFILE_JSON:"

    if marker:
        after = text.split(marker, 1)[-1].strip()

        # Try raw JSON object first
        brace = after.find("{")
        if brace >= 0:
            depth, end = 0, brace
            for i, ch in enumerate(after[brace:], brace):
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        end = i
                        break
            try:
                candidate = after[brace:end + 1]
                json.loads(candidate)   # validate
                return candidate
            except Exception:
                pass

        # Fallback: parse key: value lines
        profile = {
            "completed_courses": [],
            "grades": {},
            "target_term": "Fall 2026",
            "max_credits": 48,
            "major": "6-3",
            "catalog_year": "2025-2026",
            "transfer_credits": [],
        }
        for line in after.splitlines():
            line = line.strip()
            if ":" not in line:
                continue
            key, _, val = line.partition(":")
            key = key.strip().lower().replace(" ", "_")
            val = val.strip()
            if not val or val.lower() in ("none", ""):
                continue

            if key == "completed_courses":
                profile["completed_courses"] = [
                    c.strip() for c in re.split(r"[,\s]+", val) if c.strip()
                ]
            elif key == "grades":
                for pair in re.split(r"[,;]+", val):
                    pair = pair.strip()
                    if "->" in pair:
                        c, g = pair.split("->", 1)
                    elif ":" in pair:
                        c, g = pair.split(":", 1)
                    else:
                        continue
                    profile["grades"][c.strip()] = g.strip()
            elif key == "target_term":
                profile["target_term"] = val
            elif key == "max_credits":
                try:
                    profile["max_credits"] = int(re.search(r"\d+", val).group())
                except Exception:
                    pass
            elif key == "major":
                profile["major"] = val
            elif key == "catalog_year":
                profile["catalog_year"] = val
            elif key == "transfer_credits":
                profile["transfer_credits"] = [
                    c.strip() for c in re.split(r"[,\s]+", val) if c.strip()
                ]
        return json.dumps(profile)

    # Nothing found — return empty profile
    return json.dumps({
        "completed_courses": [],
        "grades": {},
        "target_term": "Fall 2026",
        "max_credits": 48,
        "major": "6-3",
        "catalog_year": "2025-2026",
        "transfer_credits": [],
    })


# ---------------------------------------------------------------------------
# Helper — retrieval query generation
# ---------------------------------------------------------------------------

def _generate_queries(user_input: str, profile_json: str) -> list[str]:
    """Generate multiple retrieval queries from user input + profile."""
    queries = [user_input]

    # Add course-specific queries for any course codes mentioned
    course_codes = re.findall(
        r"\b6\.\d+[A-Z]?\b|\b18\.\d+[A-Z]?\b",
        user_input + " " + profile_json
    )
    for code in list(dict.fromkeys(course_codes))[:4]:   # deduplicate, max 4
        queries.append(f"{code} prerequisites requirements")

    queries.append("6-3 degree requirements foundations headers AUS")
    queries.append("MIT academic policies prerequisites credit limits pass fail")
    return queries


# ---------------------------------------------------------------------------
# Helper — target term extraction
# ---------------------------------------------------------------------------

def _extract_target_term(profile_json: str) -> str:
    try:
        p = json.loads(profile_json)
        return p.get("target_term", "Fall 2026")
    except Exception:
        return "Fall 2026"


# ---------------------------------------------------------------------------
# Stage 1: Intake
# ---------------------------------------------------------------------------

class IntakeStage:
    def __init__(self):
        self.chain = _build_chain(INTAKE_SYSTEM_PROMPT, INTAKE_HUMAN_TEMPLATE)

    def run(self, student_input: str, prior_answers: str = "") -> dict:
        raw = self.chain.invoke({
            "student_input": student_input,
            "prior_answers": prior_answers or "None",
        })
        needs_clarification = (
            "CLARIFYING_QUESTIONS:" in raw
            and "PROFILE_COMPLETE:" not in raw
            and "PROFILE_JSON:" not in raw
        )
        return {"raw": raw, "needs_clarification": needs_clarification}


# ---------------------------------------------------------------------------
# Stage 2: Multi-query retrieval
# ---------------------------------------------------------------------------

class RetrievalStage:
    def __init__(self, retriever):
        self.retriever = retriever

    def run(self, queries: list[str]) -> tuple[list, list]:
        """Run multiple queries and deduplicate results by chunk_id."""
        seen_ids = set()
        all_docs, all_citations = [], []
        for q in queries:
            docs, cites = retrieve_with_citations(self.retriever, q)
            for doc, cite in zip(docs, cites):
                chunk_id = doc.metadata.get("chunk_id", "")
                if chunk_id not in seen_ids:
                    seen_ids.add(chunk_id)
                    all_docs.append(doc)
                    all_citations.append(cite)
        return all_docs, all_citations


# ---------------------------------------------------------------------------
# Stage 3: Planner / Prereq Checker
# ---------------------------------------------------------------------------

class PlannerStage:
    def __init__(self):
        self.plan_chain   = _build_chain(PLANNER_SYSTEM_PROMPT,      PLANNER_HUMAN_TEMPLATE)
        self.prereq_chain = _build_chain(PREREQ_CHECK_SYSTEM_PROMPT, PREREQ_CHECK_HUMAN_TEMPLATE)

    def run_plan(self, profile_json: str, context: str, target_term: str) -> str:
        return self.plan_chain.invoke({
            "profile_json": profile_json,
            "context":      context,
            "target_term":  target_term,
        })

    def run_prereq_check(
        self,
        completed_courses: list,
        grades: dict,
        question: str,
        context: str,
    ) -> str:
        return self.prereq_chain.invoke({
            "completed_courses": json.dumps(completed_courses),
            "grades":            json.dumps(grades),
            "question":          question,
            "context":           context,
        })


# ---------------------------------------------------------------------------
# Stage 4: Verifier / Auditor
# ---------------------------------------------------------------------------

class VerifierStage:
    def __init__(self):
        self.chain = _build_chain(VERIFIER_SYSTEM_PROMPT, VERIFIER_HUMAN_TEMPLATE)

    def run(self, draft_response: str, context: str) -> dict:
        raw = self.chain.invoke({
            "draft_response": draft_response,
            "context":        context,
        })
        if "AUDIT_RESULT: PASS" in raw:
            audit_result = "PASS"
        elif "AUDIT_RESULT: FAIL" in raw:
            audit_result = "FAIL"
        else:
            audit_result = "NEEDS_REVISION"
        return {"raw": raw, "audit_result": audit_result}


# ---------------------------------------------------------------------------
# Top-level Assistant
# ---------------------------------------------------------------------------

class CoursePlanningAssistant:
    """
    Orchestrates the 4-stage pipeline:
      Intake -> Retrieval -> Planner -> Verifier
    """

    def __init__(self):
        print("[assistant] Initializing vector store...")
        vectorstore = get_or_build_index()
        retriever   = build_retriever(vectorstore)

        self.intake    = IntakeStage()
        self.retrieval = RetrievalStage(retriever)
        self.planner   = PlannerStage()
        self.verifier  = VerifierStage()

    # ------------------------------------------------------------------
    def run(self, user_input: str, mode: str = "auto") -> dict[str, Any]:
        """
        Main entry point.

        mode:
          "auto"   — detect whether it's a prereq question or a plan request
          "prereq" — force prerequisite check mode
          "plan"   — force course plan mode
        """
        print(f"\n[assistant] User input: {user_input[:80]}...")

        # ── Stage 1: Intake ──────────────────────────────────────────
        print("[assistant] Stage 1: Intake")

        if _is_factual_question(user_input):
            # Simple availability / professor questions — skip intake entirely
            print("[assistant] Factual question detected — skipping intake")
            profile_json = json.dumps({
                "completed_courses": [],
                "grades": {},
                "target_term": "Fall 2026",
                "max_credits": 48,
                "major": "6-3",
                "catalog_year": "2025-2026",
                "transfer_credits": [],
            })
        else:
            intake_result = self.intake.run(user_input)
            if intake_result["needs_clarification"]:
                return {
                    "stage":               "intake",
                    "response":            intake_result["raw"],
                    "needs_clarification": True,
                }
            profile_json = _extract_profile(intake_result["raw"])

        # ── Stage 2: Retrieval ───────────────────────────────────────
        print("[assistant] Stage 2: Retrieval")
        queries = _generate_queries(user_input, profile_json)
        docs, citations = self.retrieval.run(queries)
        context = format_context(docs, citations)

        # ── Stage 3: Planner ─────────────────────────────────────────
        print("[assistant] Stage 3: Planning / Prereq check")
        use_prereq_mode = (
            mode == "prereq"
            or (mode == "auto" and _is_prereq_question(user_input))
        )

        if use_prereq_mode:
            profile = json.loads(profile_json) if profile_json else {}
            draft = self.planner.run_prereq_check(
                completed_courses=profile.get("completed_courses", []),
                grades=profile.get("grades", {}),
                question=user_input,
                context=context,
            )
        else:
            target_term = _extract_target_term(profile_json)
            draft = self.planner.run_plan(
                profile_json=profile_json or "{}",
                context=context,
                target_term=target_term,
            )

        # ── Stage 4: Verifier ─────────────────────────────────────────
        print("[assistant] Stage 4: Verification")
        audit = self.verifier.run(draft, context)

        final_response = draft
        if audit["audit_result"] == "NEEDS_REVISION":
            raw = audit["raw"]
            if "REVISED_RESPONSE:" in raw:
                revised = raw.split("REVISED_RESPONSE:", 1)[-1].strip()
                if revised.lower() != "none" and len(revised) > 20:
                    final_response = revised
                    print("[assistant] Response revised by verifier.")

        return {
            "stage":               "complete",
            "response":            final_response,
            "audit_result":        audit["audit_result"],
            "audit_details":       audit["raw"],
            "citations_retrieved": citations,
            "needs_clarification": False,
        }

    # ------------------------------------------------------------------
    def run_prereq_check(
        self,
        completed_courses: list[str],
        grades: dict[str, str],
        question: str,
    ) -> dict[str, Any]:
        """Convenience method for direct prerequisite checking."""
        print(f"\n[assistant] Prereq check: {question[:80]}...")

        queries = (
            [question]
            + [f"prerequisites for {question}"]
            + [f"{c} prerequisite requirements" for c in completed_courses[:3]]
            + ["6-3 degree requirements foundations headers"]
            + ["MIT academic policies prerequisites grade minimum"]
        )

        docs, citations = self.retrieval.run(queries)
        context = format_context(docs, citations)

        draft = self.planner.run_prereq_check(
            completed_courses=completed_courses,
            grades=grades,
            question=question,
            context=context,
        )

        audit = self.verifier.run(draft, context)

        final = draft
        if audit["audit_result"] == "NEEDS_REVISION":
            raw = audit["raw"]
            if "REVISED_RESPONSE:" in raw:
                revised = raw.split("REVISED_RESPONSE:", 1)[-1].strip()
                if revised.lower() != "none" and len(revised) > 20:
                    final = revised

        return {
            "response":     final,
            "audit_result": audit["audit_result"],
            "citations":    citations,
        }
