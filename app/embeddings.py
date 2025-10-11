"""
embeddings.py

Responsibilities:
- Split (chunk) long documents into smaller overlapping pieces.
- Create embeddings for each chunk using sentence-transformers.
- Provide utility functions to save/load chunks and embeddings.

Note: this file uses sentence-transformers by default. You can later swap to an OpenAI
embedding implementation if you prefer (then you'll need an API key).
"""

from typing import List, Tuple
import os
import json
import numpy as np

# LangChain text splitter (helps with robust chunking)
from langchain.text_splitter import RecursiveCharacterTextSplitter

# SentenceTransformers embedding model
from sentence_transformers import SentenceTransformer

# Path to save outputs (chunks + embeddings)
DEFAULT_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "embeddings")

# Initialize embedding model once (small + fast for dev)
# "all-MiniLM-L6-v2" is a good default for many semantic-search tasks.
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
_embedding_model = None


def get_embedding_model():
    """Load (or return cached) embedding model."""
    global _embedding_model
    if _embedding_model is None:
        print(f"[embeddings] Loading SentenceTransformer model: {EMBEDDING_MODEL_NAME} (this may take a few seconds)...")
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _embedding_model


def chunk_document(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> List[str]:
    """
    Split a document into character-based overlapping chunks.

    Args:
        text: full document string
        chunk_size: target characters per chunk
        chunk_overlap: overlap between consecutive chunks (characters)

    Returns:
        List of chunk strings
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len
    )
    chunks = splitter.split_text(text)
    return chunks


def embed_chunks(chunks: List[str]) -> np.ndarray:
    """
    Convert a list of text chunks into vector embeddings (numpy array).

    Returns:
        2D numpy array with shape (num_chunks, embedding_dim)
    """
    model = get_embedding_model()
    embeddings = model.encode(chunks, show_progress_bar=True)  # returns list of vectors
    return np.array(embeddings)


def save_embeddings(chunks: List[str], embeddings: np.ndarray, output_dir: str = DEFAULT_OUTPUT_DIR):
    """
    Save chunks and embeddings to disk:
    - chunks.json => list of chunks and metadata
    - vectors.npy => numpy array of embeddings

    Files:
      <output_dir>/chunks.json
      <output_dir>/vectors.npy
    """
    os.makedirs(output_dir, exist_ok=True)

    chunks_path = os.path.join(output_dir, "chunks.json")
    vectors_path = os.path.join(output_dir, "vectors.npy")

    # Save chunks + minimal metadata (index + text)
    serialized = [{"id": i, "text": chunks[i]} for i in range(len(chunks))]
    with open(chunks_path, "w", encoding="utf-8") as f:
        json.dump(serialized, f, ensure_ascii=False, indent=2)

    # Save embedding vectors as numpy binary
    np.save(vectors_path, embeddings)

    print(f"[embeddings] Saved {len(chunks)} chunks to {chunks_path}")
    print(f"[embeddings] Saved embeddings (shape: {embeddings.shape}) to {vectors_path}")


def load_embeddings(output_dir: str = DEFAULT_OUTPUT_DIR) -> Tuple[List[dict], np.ndarray]:
    """
    Load previously-saved chunks and vectors from disk.

    Returns:
        (chunks_list, embeddings_array)
        where chunks_list is a list of dicts: {"id": int, "text": str}
    """
    chunks_path = os.path.join(output_dir, "chunks.json")
    vectors_path = os.path.join(output_dir, "vectors.npy")

    if not os.path.exists(chunks_path) or not os.path.exists(vectors_path):
        raise FileNotFoundError("Saved embeddings not found. Run save_embeddings first.")

    with open(chunks_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    embeddings = np.load(vectors_path)
    print(f"[embeddings] Loaded {len(chunks)} chunks and embeddings with shape {embeddings.shape}")
    return chunks, embeddings


if __name__ == "__main__":
    # Quick local demo when running the file directly
    demo_path = os.path.join(os.path.dirname(__file__), "..", "data", "sample.txt")
    if not os.path.exists(demo_path):
        print(f"No sample file found at {demo_path}. Place a sample.txt in data/ and re-run.")
        raise SystemExit(1)

    with open(demo_path, "r", encoding="utf-8") as f:
        text = f.read()

    chunks = chunk_document(text)
    print(f"[demo] Created {len(chunks)} chunks (first 2 chunks preview):")
    for i, c in enumerate(chunks[:2]):
        print(f"--- CHUNK {i} ---\n{c}\n")

    vectors = embed_chunks(chunks)
    save_embeddings(chunks, vectors)
