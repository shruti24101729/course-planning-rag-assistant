"""
app.py — Streamlit demo for MIT Course Planning RAG Assistant
Run: streamlit run app.py
"""

import streamlit as st
import sys
import os
import re

sys.path.insert(0, os.path.dirname(__file__))

st.set_page_config(
    page_title="MIT Course Planning Assistant",
    page_icon="🎓",
    layout="wide",
)

st.markdown("""
<style>
    .stApp { background-color: #f5f3ff; }

    .header-box {
        background: linear-gradient(135deg, #5B2D8E, #8B5CF6);
        padding: 1.4rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.2rem;
    }
    .header-box h1 { color: white; margin: 0; font-size: 1.7rem; }
    .header-box p  { color: #e8d5ff; margin: 0.3rem 0 0 0; font-size: 0.9rem; }

    .audit-pass {
        display: inline-block;
        background: #d4edda; color: #155724;
        padding: 3px 12px; border-radius: 20px;
        font-size: 0.8rem; font-weight: 600; margin-top: 6px;
    }
    .audit-fail {
        display: inline-block;
        background: #f8d7da; color: #721c24;
        padding: 3px 12px; border-radius: 20px;
        font-size: 0.8rem; font-weight: 600; margin-top: 6px;
    }
    .audit-revise {
        display: inline-block;
        background: #fff3cd; color: #856404;
        padding: 3px 12px; border-radius: 20px;
        font-size: 0.8rem; font-weight: 600; margin-top: 6px;
    }

    .stButton > button {
        background: linear-gradient(135deg, #5B2D8E, #8B5CF6);
        color: white; border: none; border-radius: 8px;
        padding: 0.4rem 1rem; font-weight: 600;
        width: 100%; font-size: 0.78rem;
    }
    .stButton > button:hover { opacity: 0.88; }
</style>
""", unsafe_allow_html=True)


# ── Load assistant ────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner="Loading catalog index...")
def load_assistant():
    from src.chain import CoursePlanningAssistant
    return CoursePlanningAssistant()


# ── Session state ─────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="header-box">
    <h1>🎓 MIT Course Planning Assistant</h1>
    <p>Catalog-grounded &nbsp;·&nbsp; Citation-backed &nbsp;·&nbsp; GPT-4o + LangChain RAG</p>
</div>
""", unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Mode")
    mode = st.radio(
        "Query Mode",
        ["🤖 Auto Detect", "✅ Prerequisite Check", "📅 Course Plan"],
        index=0,
    )
    mode_map = {
        "🤖 Auto Detect":        "auto",
        "✅ Prerequisite Check":  "prereq",
        "📅 Course Plan":         "plan",
    }

    st.markdown("---")
    st.markdown("### 📚 Student Profile")
    completed = st.text_area(
        "Completed Courses",
        placeholder="e.g. 6.009, 18.01, 6.042J",
        height=80,
    )
    grades_input = st.text_area(
        "Grades (optional)",
        placeholder="e.g. 6.009:A, 18.01:B",
        height=70,
    )

    st.markdown("---")
    st.markdown("### 💡 Quick Examples")
    examples = [
        "Can I take 6.006 if I completed 6.009 and 6.042J?",
        "What is the full prereq chain to take 6.814?",
        "Plan my Fall 2026 semester. Max 48 units.",
        "Can I take Foundation subjects on Pass/Fail?",
        "Who is teaching 6.006 in Fall 2026?",
    ]
    for ex in examples:
        label = ex[:42] + "..." if len(ex) > 42 else ex
        if st.button(label, key=ex):
            st.session_state["prefill"] = ex

    st.markdown("---")
    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.rerun()

    st.markdown("---")
    st.markdown("### 📊 Session Stats")
    total  = len([m for m in st.session_state.messages if m["role"] == "assistant"])
    cited  = len([m for m in st.session_state.messages
                  if m["role"] == "assistant" and m.get("citations")])
    passed = len([m for m in st.session_state.messages
                  if m["role"] == "assistant" and m.get("audit") == "PASS"])
    st.metric("Total Queries",  total)
    st.metric("With Citations", cited)
    st.metric("Audit PASS",     passed)


# ── Helpers ───────────────────────────────────────────────────────────────────
def parse_courses(text):
    if not text.strip():
        return []
    return [c.strip() for c in re.split(r"[,\s]+", text.strip()) if c.strip()]


def parse_grades(text):
    grades = {}
    if not text.strip():
        return grades
    for pair in re.split(r"[,;]+", text.strip()):
        pair = pair.strip()
        if ":" in pair:
            c, g = pair.split(":", 1)
            grades[c.strip()] = g.strip()
    return grades


def get_response(result: dict) -> str:
    """
    Safely pull the response string out of the result dict.
    Tries multiple keys so nothing is lost.
    """
    # Primary key
    resp = result.get("response", "")
    if isinstance(resp, str):
        resp = resp.strip()

    # If empty, try alternate keys
    if not resp:
        for key in ("output", "text", "answer"):
            val = result.get(key, "")
            if isinstance(val, str) and val.strip():
                resp = val.strip()
                break

    # If still empty, dig into audit_details for REVISED_RESPONSE
    if not resp or len(resp) < 10:
        audit_raw = result.get("audit_details", "")
        if isinstance(audit_raw, str) and "REVISED_RESPONSE:" in audit_raw:
            candidate = audit_raw.split("REVISED_RESPONSE:", 1)[-1].strip()
            if candidate.lower() not in ("none", "") and len(candidate) > 10:
                resp = candidate

    if not resp or len(resp) < 5:
        resp = "Could not generate a response. Please try again."

    return resp


def display_response(response: str, citations: list, audit: str):
    """Render assistant reply cleanly."""

    # Split response into labelled sections and display each
    sections = {
        "DECISION":   "🟢 Decision",
        "EVIDENCE":   "📋 Evidence",
        "REASONING":  "🔍 Reasoning",
        "NEXT STEP":  "➡️ Next Step",
        "CITATIONS":  "📎 Citations",
        "ANSWER / PLAN": "📅 Answer / Plan",
        "SUGGESTED COURSES": "📚 Suggested Courses",
        "TOTAL CREDITS": "🎯 Total Credits",
        "RISKS / ASSUMPTIONS": "⚠️ Risks / Assumptions",
        "CLARIFYING QUESTIONS": "❓ Clarifying Questions",
    }

    # Try to detect if structured (has known section headers)
    has_sections = any(key + ":" in response for key in sections)

    if has_sections:
        # Parse and display section by section
        lines = response.splitlines()
        current_section = None
        buffer = []

        for line in lines:
            matched = False
            for key, label in sections.items():
                if line.strip().startswith(key + ":"):
                    # Flush previous section
                    if current_section and buffer:
                        st.markdown(f"**{current_section}**")
                        st.write("\n".join(buffer).strip())
                        st.markdown("---")
                        buffer = []
                    current_section = label
                    rest = line.strip()[len(key)+1:].strip()
                    if rest:
                        buffer.append(rest)
                    matched = True
                    break
            if not matched:
                buffer.append(line)

        # Flush last section
        if current_section and buffer:
            st.markdown(f"**{current_section}**")
            st.write("\n".join(buffer).strip())
            st.markdown("---")
        elif buffer:
            # No sections matched at all — just show everything
            st.write("\n".join(buffer).strip())

    else:
        # Plain response — just show it
        st.write(response)

    # Citations expander
    if citations:
        with st.expander(f"📎 {len(citations)} Source Citations", expanded=True):
            for c in citations[:8]:
                st.markdown(f"- `{c}`")

    # Audit badge
    css = ("audit-pass"   if audit == "PASS"
           else "audit-revise" if audit == "NEEDS_REVISION"
           else "audit-fail")
    st.markdown(
        f'<span class="{css}">Audit: {audit}</span>',
        unsafe_allow_html=True,
    )


# ── Show chat history ─────────────────────────────────────────────────────────
st.markdown("### 💬 Chat")

for msg in st.session_state.messages:
    if msg["role"] == "user":
        with st.chat_message("user"):
            st.write(msg["content"])
    else:
        with st.chat_message("assistant", avatar="🎓"):
            display_response(
                response=msg["content"],
                citations=msg.get("citations", []),
                audit=msg.get("audit", "N/A"),
            )


# ── Chat input ────────────────────────────────────────────────────────────────
prefill    = st.session_state.pop("prefill", "")
user_input = st.chat_input("Ask about prerequisites, course plans, degree requirements...")

if prefill and not user_input:
    user_input = prefill

if user_input:
    # Save and show user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    with st.spinner("🔍 Searching catalog and generating answer..."):
        try:
            assistant      = load_assistant()
            completed_list = parse_courses(completed)
            grades_dict    = parse_grades(grades_input)
            selected_mode  = mode_map[mode]

            # Detect routing
            is_prereq = (
                selected_mode == "prereq"
                or (
                    selected_mode == "auto"
                    and any(k in user_input.lower() for k in [
                        "can i take", "eligible", "prerequisite",
                        "prereq", "what do i need", "co-requisite",
                        "am i allowed", "do i qualify",
                    ])
                )
            )

            # Call the right method
            if is_prereq and completed_list:
                result = assistant.run_prereq_check(
                    completed_courses=completed_list,
                    grades=grades_dict,
                    question=user_input,
                )
            else:
                enriched = user_input
                if completed_list:
                    enriched += (
                        f"\n\nStudent profile: completed={completed_list}, "
                        f"grades={grades_dict}, major=6-3, "
                        f"catalog_year=2025-2026"
                    )
                result = assistant.run(enriched, mode=selected_mode)

            # Extract all fields
            response  = get_response(result)
            citations = result.get("citations", result.get("citations_retrieved", []))
            audit     = result.get("audit_result", "N/A")

            # Save to history
            st.session_state.messages.append({
                "role":      "assistant",
                "content":   response,
                "citations": citations,
                "audit":     audit,
            })

            # Display
            with st.chat_message("assistant", avatar="🎓"):
                display_response(response, citations, audit)

        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            st.info(
                "Make sure OPENAI_API_KEY is set and index is built:\n"
                "`python main.py --build-index`"
            )
