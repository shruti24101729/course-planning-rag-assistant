"""
ingest.py — Document ingestion, chunking, embedding, and FAISS index building.

Chunking strategy:
  - Chunk size: 600 tokens (~450 words) with 100-token overlap
  - Rationale: Course catalog entries vary 50–300 words each; 600 tokens captures
    a full entry plus surrounding context without losing multi-section prerequisite
    chains. Overlap ensures boundaries don't split a prerequisite list mid-sentence.
  - Separator hierarchy: double-newline > single newline > space
  - Each chunk retains metadata: source filename, section heading, chunk_id
"""

import os
import glob
import hashlib
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file


DATA_DIR = Path(__file__).parent.parent / "data" / "catalog"
FAISS_INDEX_DIR = Path(__file__).parent.parent / "faiss_index"

CHUNK_SIZE = 600        # tokens (approx)
CHUNK_OVERLAP = 100     # tokens


def load_documents(data_dir: Path) -> list[Document]:
    """Load all .txt catalog files from data_dir."""
    docs = []
    for filepath in sorted(glob.glob(str(data_dir / "*.txt"))):
        text = Path(filepath).read_text(encoding="utf-8")
        filename = Path(filepath).name
        # Extract source URL and date from header comments
        source_url = _extract_field(text, "URL:")
        date_accessed = _extract_field(text, "DATE ACCESSED:")
        coverage = _extract_field(text, "COVERAGE:")
        docs.append(Document(
            page_content=text,
            metadata={
                "source_file": filename,
                "source_url": source_url,
                "date_accessed": date_accessed,
                "coverage": coverage,
            }
        ))
    print(f"[ingest] Loaded {len(docs)} documents from {data_dir}")
    return docs


def _extract_field(text: str, field: str) -> str:
    for line in text.splitlines():
        if line.startswith(field):
            return line[len(field):].strip()
    return "unknown"


def chunk_documents(docs: list[Document]) -> list[Document]:
    """Split documents into overlapping chunks with metadata."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", " ", ""],
        length_function=len,
    )
    chunks = []
    for doc in docs:
        splits = splitter.split_documents([doc])
        for i, chunk in enumerate(splits):
            # Generate a stable chunk_id
            chunk_id = hashlib.md5(
                f"{doc.metadata['source_file']}_{i}".encode()
            ).hexdigest()[:8]
            chunk.metadata["chunk_id"] = chunk_id
            chunk.metadata["chunk_index"] = i
            # Extract nearest section heading from chunk content
            chunk.metadata["section_heading"] = _nearest_heading(chunk.page_content)
            chunks.append(chunk)
    print(f"[ingest] Created {len(chunks)} chunks "
          f"(size≈{CHUNK_SIZE}, overlap≈{CHUNK_OVERLAP})")
    return chunks


def _nearest_heading(text: str) -> str:
    """Heuristically extract the nearest section heading from chunk text."""
    for line in text.splitlines():
        line = line.strip()
        if line and (line.isupper() or line.startswith("SECTION") or
                     line.startswith("===") or
                     (len(line) < 80 and line.endswith("=="))):
            return line[:80]
    return "N/A"


def build_faiss_index(chunks: list[Document], index_dir: Path) -> FAISS:
    """Embed chunks and persist a FAISS index."""
    print("[ingest] Building FAISS index with OpenAI embeddings...")
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vectorstore = FAISS.from_documents(chunks, embeddings)
    index_dir.mkdir(parents=True, exist_ok=True)
    vectorstore.save_local(str(index_dir))
    print(f"[ingest] FAISS index saved to {index_dir}")
    return vectorstore


def load_faiss_index(index_dir: Path) -> FAISS:
    """Load a previously-built FAISS index."""
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vectorstore = FAISS.load_local(
        str(index_dir), embeddings, allow_dangerous_deserialization=True
    )
    print(f"[ingest] Loaded FAISS index from {index_dir}")
    return vectorstore


def get_or_build_index() -> FAISS:
    """Return existing index if available, otherwise build it."""
    if (FAISS_INDEX_DIR / "index.faiss").exists():
        return load_faiss_index(FAISS_INDEX_DIR)
    docs = load_documents(DATA_DIR)
    chunks = chunk_documents(docs)
    return build_faiss_index(chunks, FAISS_INDEX_DIR)


if __name__ == "__main__":
    vs = get_or_build_index()
    print("[ingest] Index ready. Testing a sample query...")
    results = vs.similarity_search("prerequisites for 6.006", k=3)
    for r in results:
        print(f"  chunk_id={r.metadata.get('chunk_id')} "
              f"file={r.metadata.get('source_file')}")
        print(f"  {r.page_content[:120]}...\n")
