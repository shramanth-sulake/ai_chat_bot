"""
ingest_sample.py

Small helper script to call app.embeddings functions from the project root.
Run this to create chunks + embeddings and save them under data/embeddings/.
"""

from app.embeddings import chunk_document, embed_chunks, save_embeddings
import os
import sys

def main():
    sample_path = os.path.join("data", "sample.txt")
    if not os.path.exists(sample_path):
        print("Please add a sample document at data/sample.txt and re-run.")
        sys.exit(1)

    with open(sample_path, "r", encoding="utf-8") as f:
        text = f.read()

    print("[ingest] Chunking document...")
    chunks = chunk_document(text)
    print(f"[ingest] {len(chunks)} chunks created")

    print("[ingest] Embedding chunks...")
    vectors = embed_chunks(chunks)
    print(f"[ingest] Embeddings shape: {vectors.shape}")

    print("[ingest] Saving to disk...")
    save_embeddings(chunks, vectors)
    print("[ingest] Done.")

if __name__ == "__main__":
    main()
