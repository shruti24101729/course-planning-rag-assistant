"""
retriever.py — Retriever configuration wrapping the FAISS vector store.

Settings:
  k = 6       — return top-6 chunks per query (balances recall vs. context window)
  metric      — cosine similarity (FAISS inner-product on normalized vectors)
  score_threshold — 0.25 minimum similarity; chunks below this are discarded
                    to prevent weak/irrelevant evidence from being cited

Citation format returned per chunk:
  [source_file § section_heading (chunk_id)]
"""

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

TOP_K = 6
SCORE_THRESHOLD = 0.15   # cosine similarity (0–1 scale after normalization)


def build_retriever(vectorstore: FAISS):
    """Return a LangChain retriever with score-threshold filtering."""
    return vectorstore.as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs={
            "k": TOP_K,
            "score_threshold": SCORE_THRESHOLD,
        },
    )


def retrieve_with_citations(
    retriever, query: str
) -> tuple[list[Document], list[str]]:
    """
    Run a retrieval query and return (docs, citation_strings).

    citation_strings format:
      "[<source_file> § <section_heading> (chunk_id=<id>)]"
    """
    docs = retriever.invoke(query)
    citations = []
    for doc in docs:
        m = doc.metadata
        url = m.get("source_url", "URL unknown")
        section = m.get("section_heading", "N/A")
        chunk_id = m.get("chunk_id", "??")
        citations.append(
            f"[{m.get('source_file', 'unknown')} § {section} "
            f"(chunk_id={chunk_id}) | URL: {url}]"
        )
    return docs, citations


def format_context(docs: list[Document], citations: list[str]) -> str:
    """Format retrieved chunks as a context block with inline citation labels."""
    parts = []
    for i, (doc, cite) in enumerate(zip(docs, citations)):
        parts.append(f"--- Context [{i+1}] {cite} ---\n{doc.page_content.strip()}")
    return "\n\n".join(parts)
