"""
eval_queries.py — 25-query evaluation set for the Course Planning Assistant.

Categories:
  A. Prerequisite checks (10)     — eligible / not eligible
  B. Prerequisite chain questions (5) — multi-hop
  C. Program requirement questions (5) — electives, credits, categories
  D. Not-in-docs / trick questions (5) — must abstain or escalate

Format per query:
  {
    "id": str,
    "category": "A"|"B"|"C"|"D",
    "query": str,
    "completed_courses": list[str],
    "grades": dict,
    "expected_decision": str,   # "eligible"|"not_eligible"|"need_more_info"|"abstain"
    "expected_citation_present": bool,
    "rubric_note": str,
  }
"""

EVAL_QUERIES = [

    # ============================================================
    # A. PREREQUISITE CHECKS (10)
    # ============================================================

    {
        "id": "A01",
        "category": "A_prereq_check",
        "query": "Can I take 6.006 if I have completed 6.009 and 18.01?",
        "completed_courses": ["6.009", "18.01"],
        "grades": {"6.009": "B", "18.01": "A"},
        "expected_decision": "need_more_info",
        "expected_citation_present": True,
        "rubric_note": (
            "6.006 requires 6.009 AND (6.042J or concurrent 6.042J). "
            "Student has 6.009 but NOT 6.042J. Correct answer: Not eligible unless "
            "enrolling in 6.042J concurrently. Citation required from mit_cs_courses.txt."
        ),
    },

    {
        "id": "A02",
        "category": "A_prereq_check",
        "query": "Am I eligible for 6.006 if I've completed 6.009 and 6.042J?",
        "completed_courses": ["6.009", "6.042J"],
        "grades": {"6.009": "A", "6.042J": "B"},
        "expected_decision": "eligible",
        "expected_citation_present": True,
        "rubric_note": (
            "Both required prerequisites present. Eligible. "
            "Citation: mit_cs_courses.txt § 6.006 entry."
        ),
    },

    {
        "id": "A03",
        "category": "A_prereq_check",
        "query": "Can I enroll in 6.036 if I have completed 6.006 and 18.06 but not 18.650?",
        "completed_courses": ["6.006", "18.06"],
        "grades": {"6.006": "B", "18.06": "B"},
        "expected_decision": "need_more_info",
        "expected_citation_present": True,
        "rubric_note": (
            "6.036 requires: 6.006; 18.06 or 18.C06J; 18.650 or 6.041B or permission. "
            "Student is missing 18.650/6.041B but permission of instructor is listed as "
            "an alternative. Decision: Need More Info — must confirm instructor permission."
        ),
    },

    {
        "id": "A04",
        "category": "A_prereq_check",
        "query": "Can I take 6.814 Database Systems if I've only taken 6.006 and 6.031?",
        "completed_courses": ["6.006", "6.031"],
        "grades": {"6.006": "A", "6.031": "A"},
        "expected_decision": "not_eligible",
        "expected_citation_present": True,
        "rubric_note": (
            "6.814 requires 6.033 as prerequisite. Student has not completed 6.033. "
            "Not eligible. Citation: mit_cs_courses.txt § 6.814."
        ),
    },

    {
        "id": "A05",
        "category": "A_prereq_check",
        "query": "I finished 6.033. Can I now take 6.824?",
        "completed_courses": ["6.033", "6.004"],
        "grades": {"6.033": "B", "6.004": "A"},
        "expected_decision": "eligible",
        "expected_citation_present": True,
        "rubric_note": (
            "6.824 requires 6.033 and 6.004. Student has both. Eligible. "
            "Citation: mit_cs_courses.txt § 6.824."
        ),
    },

    {
        "id": "A06",
        "category": "A_prereq_check",
        "query": "Can a freshman with no MIT subjects taken enroll in 6.004?",
        "completed_courses": [],
        "grades": {},
        "expected_decision": "not_eligible",
        "expected_citation_present": True,
        "rubric_note": (
            "6.004 requires 6.009. Student has no completed courses. Not eligible. "
            "Also, academic policy states freshmen may not enroll in 6.004 without "
            "completing 6.009. Citations: mit_cs_courses.txt + mit_6_3_requirements.txt."
        ),
    },

    {
        "id": "A07",
        "category": "A_prereq_check",
        "query": "I got a D in 6.009. Does that satisfy the prerequisite for 6.004?",
        "completed_courses": ["6.009"],
        "grades": {"6.009": "D"},
        "expected_decision": "eligible",
        "expected_citation_present": True,
        "rubric_note": (
            "Academic policies state a passing grade (D or above) normally satisfies "
            "a prerequisite unless the course catalog entry specifies otherwise. "
            "6.004 does not specify a minimum grade beyond 'completion of 6.009'. "
            "Decision: Eligible (with caveat about instructor discretion). "
            "Citation: mit_academic_policies.txt § B.3 and mit_6_3_requirements.txt."
        ),
    },

    {
        "id": "A08",
        "category": "A_prereq_check",
        "query": "Can I take 6.046J if I passed 6.006 with a C?",
        "completed_courses": ["6.006"],
        "grades": {"6.006": "C"},
        "expected_decision": "eligible",
        "expected_citation_present": True,
        "rubric_note": (
            "6.046J requires 6.006. A grade of C is a passing grade (3.0 on MIT scale). "
            "No minimum grade above D is specified for 6.006 prerequisite. Eligible. "
            "Citation: mit_cs_courses.txt § 6.046J; mit_academic_policies.txt § B.3."
        ),
    },

    {
        "id": "A09",
        "category": "A_prereq_check",
        "query": "I want to take 6.042J. I have completed 18.01. Am I eligible?",
        "completed_courses": ["18.01"],
        "grades": {"18.01": "B"},
        "expected_decision": "eligible",
        "expected_citation_present": True,
        "rubric_note": (
            "6.042J requires Calculus I (18.01 or equivalent). Student has 18.01. Eligible. "
            "Citation: mit_cs_courses.txt § 6.042J."
        ),
    },

    {
        "id": "A10",
        "category": "A_prereq_check",
        "query": "Can I take 6.858 Computer Systems Security if I've completed 6.046J but not 6.033?",
        "completed_courses": ["6.046J"],
        "grades": {"6.046J": "A"},
        "expected_decision": "not_eligible",
        "expected_citation_present": True,
        "rubric_note": (
            "6.858 requires 6.033. Student has 6.046J but not 6.033. Not eligible. "
            "Citation: mit_cs_courses.txt § 6.858."
        ),
    },

    # ============================================================
    # B. PREREQUISITE CHAIN QUESTIONS (5) — multi-hop
    # ============================================================

    {
        "id": "B01",
        "category": "B_chain",
        "query": "What is the full prerequisite chain to take 6.814 Database Systems from scratch (no courses completed)?",
        "completed_courses": [],
        "grades": {},
        "expected_decision": "eligible",  # the chain itself is the answer
        "expected_citation_present": True,
        "rubric_note": (
            "Full chain: 6.009 → 6.004 → 6.033 → 6.814. "
            "Must cite each hop: 6.004 prereq=6.009; 6.033 prereq=6.004+6.009; "
            "6.814 prereq=6.033. All in mit_cs_courses.txt."
        ),
    },

    {
        "id": "B02",
        "category": "B_chain",
        "query": "What courses must I complete before I can take 6.867 Machine Learning graduate course?",
        "completed_courses": [],
        "grades": {},
        "expected_decision": "need_more_info",
        "expected_citation_present": True,
        "rubric_note": (
            "6.867 requires: 6.036; 18.06; 18.650 or 6.041. "
            "6.036 itself requires: 6.006; 18.06 or 18.C06J; 18.650 or 6.041B. "
            "6.006 requires: 6.009; 6.042J. Chain: 18.01→18.02→18.06; "
            "6.009→6.042J→6.006→6.036→6.867. 2+ citation hops required."
        ),
    },

    {
        "id": "B03",
        "category": "B_chain",
        "query": "I have completed 6.009 and 6.042J. What is the fastest path to 6.824 Distributed Systems?",
        "completed_courses": ["6.009", "6.042J"],
        "grades": {"6.009": "A", "6.042J": "A"},
        "expected_decision": "eligible",
        "expected_citation_present": True,
        "rubric_note": (
            "6.824 requires 6.033 and 6.004. "
            "6.033 requires 6.004 and 6.009. 6.004 requires 6.009. "
            "Student has 6.009. Path: Take 6.004 → then 6.033 → then 6.824 (3 terms). "
            "Or 6.004+6.006 concurrently (already has prereqs for 6.006 too). "
            "Must cite mit_cs_courses.txt for each course."
        ),
    },

    {
        "id": "B04",
        "category": "B_chain",
        "query": "Can I take 6.035 Computer Language Engineering if I have completed 6.009 and 6.006?",
        "completed_courses": ["6.009", "6.006"],
        "grades": {"6.009": "B", "6.006": "B"},
        "expected_decision": "not_eligible",
        "expected_citation_present": True,
        "rubric_note": (
            "6.035 requires 6.004 AND 6.031. Student has 6.009 and 6.006 but "
            "not 6.004 or 6.031. Not eligible. Two missing prerequisites. "
            "Citation: mit_cs_courses.txt § 6.035."
        ),
    },

    {
        "id": "B05",
        "category": "B_chain",
        "query": "I completed 6.009, 18.01, 18.02, and 18.06. Can I go straight to 6.036?",
        "completed_courses": ["6.009", "18.01", "18.02", "18.06"],
        "grades": {"6.009": "A", "18.01": "A", "18.02": "A", "18.06": "A"},
        "expected_decision": "not_eligible",
        "expected_citation_present": True,
        "rubric_note": (
            "6.036 requires 6.006 (which requires 6.009 and 6.042J) AND "
            "18.06 AND (18.650 or 6.041B or permission). Student has 18.06 and 6.009 "
            "but is missing 6.006 and 18.650/6.041B. Not eligible; needs 6.006 first."
        ),
    },

    # ============================================================
    # C. PROGRAM REQUIREMENT QUESTIONS (5)
    # ============================================================

    {
        "id": "C01",
        "category": "C_program_req",
        "query": "How many AUS subjects do I need to graduate from 6-3, and what are the category rules?",
        "completed_courses": [],
        "grades": {},
        "expected_decision": "eligible",
        "expected_citation_present": True,
        "rubric_note": (
            "Requires 3 AUS total: at least 1 Systems AUS and at least 1 Theory/AI AUS. "
            "Citation: mit_6_3_requirements.txt § SECTION 2."
        ),
    },

    {
        "id": "C02",
        "category": "C_program_req",
        "query": "Does 6.814 count as an AUS for the 6-3 degree, and which category?",
        "completed_courses": [],
        "grades": {},
        "expected_decision": "eligible",
        "expected_citation_present": True,
        "rubric_note": (
            "6.814 is listed under Systems AUS. Counts as AUS (Systems category). "
            "Citation: mit_6_3_requirements.txt § SECTION 2 Systems AUS."
        ),
    },

    {
        "id": "C03",
        "category": "C_program_req",
        "query": "What is the minimum total units required to graduate with a 6-3 degree?",
        "completed_courses": [],
        "grades": {},
        "expected_decision": "eligible",
        "expected_citation_present": True,
        "rubric_note": (
            "Minimum 180 units total. Citation: mit_6_3_requirements.txt § SECTION 4."
        ),
    },

    {
        "id": "C04",
        "category": "C_program_req",
        "query": "Can I take my required subjects (Foundations and Headers) on a Pass/Fail basis?",
        "completed_courses": [],
        "grades": {},
        "expected_decision": "not_eligible",
        "expected_citation_present": True,
        "rubric_note": (
            "Academic policies explicitly state required departmental subjects "
            "(Foundations and Headers) CANNOT be taken P/F. AUS also cannot be P/F. "
            "Citation: mit_academic_policies.txt § A.2."
        ),
    },

    {
        "id": "C05",
        "category": "C_program_req",
        "query": "Does 6.033 satisfy the CI-M requirement for 6-3?",
        "completed_courses": [],
        "grades": {},
        "expected_decision": "eligible",
        "expected_citation_present": True,
        "rubric_note": (
            "6.033 is listed as a CI-M subject and satisfies the communication-intensive "
            "requirement. Citation: mit_6_3_requirements.txt § SECTION 2 and "
            "mit_cs_courses.txt § 6.033 entry."
        ),
    },

    # ============================================================
    # D. NOT-IN-DOCS / TRICK QUESTIONS (5) — must abstain
    # ============================================================

    {
        "id": "D01",
        "category": "D_not_in_docs",
        "query": "Is 6.006 being offered in Fall 2026 and who is teaching it?",
        "completed_courses": [],
        "grades": {},
        "expected_decision": "abstain",
        "expected_citation_present": False,
        "rubric_note": (
            "Course availability and instructor assignment for a specific future term "
            "are NOT in the catalog documents. Must abstain and point to "
            "MIT Schedule of Classes (student.mit.edu)."
        ),
    },

    {
        "id": "D02",
        "category": "D_not_in_docs",
        "query": "Can the professor of 6.036 waive the 18.650 requirement if I email them?",
        "completed_courses": [],
        "grades": {},
        "expected_decision": "abstain",
        "expected_citation_present": False,
        "rubric_note": (
            "Policy says instructor consent CAN waive prerequisites, but whether a "
            "specific instructor will agree to waive 18.650 for 6.036 is not in the docs. "
            "Should cite the general instructor consent policy but abstain on the "
            "specific professor's decision. Recommend contacting the instructor directly."
        ),
    },

    {
        "id": "D03",
        "category": "D_not_in_docs",
        "query": "What is the average GPA of students who take 6.046J?",
        "completed_courses": [],
        "grades": {},
        "expected_decision": "abstain",
        "expected_citation_present": False,
        "rubric_note": (
            "Student GPA statistics are not in the catalog or policy documents. "
            "Must abstain entirely. Suggest checking MIT's Institutional Research office."
        ),
    },

    {
        "id": "D04",
        "category": "D_not_in_docs",
        "query": "How many seats are left in 6.033 for next semester?",
        "completed_courses": [],
        "grades": {},
        "expected_decision": "abstain",
        "expected_citation_present": False,
        "rubric_note": (
            "Enrollment capacity / remaining seats are not in the catalog documents. "
            "Must abstain and point to the MIT Schedule of Classes or Stellar/Canvas."
        ),
    },

    {
        "id": "D05",
        "category": "D_not_in_docs",
        "query": "If I do an internship at a FAANG company, can it count as credit toward my 6-3 degree?",
        "completed_courses": [],
        "grades": {},
        "expected_decision": "abstain",
        "expected_citation_present": False,
        "rubric_note": (
            "Internship credit policy is not covered in the provided catalog documents. "
            "The academic policies document covers transfer credit and AUS but says "
            "nothing about internship credit. Must abstain and recommend contacting "
            "the EECS Undergraduate Office (ug-eecs@mit.edu)."
        ),
    },
]


# ============================================================
# Evaluation runner
# ============================================================

def run_evaluation(assistant, save_results: bool = True) -> dict:
    """
    Run all 25 eval queries through the assistant and compute metrics.
    Returns a results dict with per-query outcomes and aggregate metrics.
    """
    import json, datetime

    results = []
    citation_hits = 0
    correct_decisions = 0
    correct_abstentions = 0
    total_abstention_queries = 0

    for q in EVAL_QUERIES:
        print(f"\n{'='*60}")
        print(f"[eval] Running {q['id']} ({q['category']}): {q['query'][:60]}...")

        if q["category"].startswith("A") or q["category"].startswith("B"):
            result = assistant.run_prereq_check(
                completed_courses=q["completed_courses"],
                grades=q["grades"],
                question=q["query"],
            )
        else:
            result = assistant.run(q["query"], mode="auto")

        response_text = result.get("response", "")
        citations = result.get("citations", result.get("citations_retrieved", []))

        # Citation coverage
        has_citation = bool(citations) and "[" in response_text
        if has_citation:
            citation_hits += 1

        # Decision correctness (keyword heuristic — manual review recommended)
        decision_correct = _check_decision(response_text, q["expected_decision"])
        if decision_correct:
            correct_decisions += 1

        # Abstention accuracy
        if q["expected_decision"] == "abstain":
            total_abstention_queries += 1
            if _is_abstention(response_text):
                correct_abstentions += 1

        query_result = {
            "id": q["id"],
            "category": q["category"],
            "query": q["query"],
            "expected_decision": q["expected_decision"],
            "response_snippet": response_text[:500],
            "citations_count": len(citations),
            "has_citation": has_citation,
            "decision_correct": decision_correct,
            "audit_result": result.get("audit_result", "N/A"),
            "rubric_note": q["rubric_note"],
        }
        results.append(query_result)
        print(f"  Citation: {'✓' if has_citation else '✗'} | "
              f"Decision: {'✓' if decision_correct else '✗'} | "
              f"Audit: {result.get('audit_result', 'N/A')}")

    total = len(EVAL_QUERIES)
    metrics = {
        "total_queries": total,
        "citation_coverage_rate": round(citation_hits / total, 3),
        "eligibility_correctness": round(correct_decisions / total, 3),
        "abstention_accuracy": round(
            correct_abstentions / total_abstention_queries, 3
        ) if total_abstention_queries else None,
        "abstention_queries": total_abstention_queries,
        "timestamp": datetime.datetime.now().isoformat(),
    }

    print(f"\n{'='*60}")
    print(f"EVALUATION SUMMARY")
    print(f"  Citation Coverage:      {metrics['citation_coverage_rate']:.1%}")
    print(f"  Decision Correctness:   {metrics['eligibility_correctness']:.1%}")
    print(f"  Abstention Accuracy:    {metrics['abstention_accuracy']:.1%}" if metrics['abstention_accuracy'] else "  Abstention: N/A")

    output = {"metrics": metrics, "results": results}

    if save_results:
        out_path = "evaluation/eval_results.json"
        import os; os.makedirs("evaluation", exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(output, f, indent=2)
        print(f"  Results saved to {out_path}")

    return output


def _check_decision(response: str, expected: str) -> bool:
    """Heuristic decision check — manual review provides final score."""
    lower = response.lower()
    if expected == "eligible":
        return "eligible" in lower and "not eligible" not in lower
    elif expected == "not_eligible":
        return "not eligible" in lower or "ineligible" in lower
    elif expected == "need_more_info":
        return "need more info" in lower or "need more information" in lower or \
               "clarif" in lower or "permission" in lower
    elif expected == "abstain":
        return _is_abstention(response)
    return False


def _is_abstention(response: str) -> bool:
    markers = [
        "don't have that information",
        "not in the provided catalog",
        "not covered in",
        "i cannot find",
        "not found in",
        "please check",
        "consult your advisor",
        "schedule of classes",
    ]
    lower = response.lower()
    return any(m in lower for m in markers)


if __name__ == "__main__":
    # Print query summary
    from collections import Counter
    cats = Counter(q["category"] for q in EVAL_QUERIES)
    print("Evaluation set summary:")
    for cat, count in sorted(cats.items()):
        print(f"  {cat}: {count} queries")
    print(f"  Total: {len(EVAL_QUERIES)} queries")
