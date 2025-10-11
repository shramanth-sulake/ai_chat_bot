"""
search.py

Implements semantic search using cosine similarity between query embeddings
and stored document embeddings.
"""

import numpy as np
from typing import List, Tuple
from app.embeddings import get_embedding_model, chunk_document, embed_chunks, load_embeddings

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    Compute cosine similarity between two vectors.
    """
    dot = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    return dot / (norm_a * norm_b + 1e-10)  # small term prevents divide-by-zero


def search(query: str, top_k: int = 3) -> List[Tuple[str, float]]:
    """
    Search for the most relevant chunks given a query.

    Args:
        query: user input question
        top_k: how many results to return

    Returns:
        List of tuples: (chunk_text, similarity_score)
    """
    # Load previously saved chunks + embeddings
    chunks, embeddings = load_embeddings()

    # Convert query into embedding
    model = get_embedding_model()
    query_vector = model.encode([query])[0]  # single vector

    # Compute similarity with each chunk vector
    scores = [cosine_similarity(query_vector, emb) for emb in embeddings]

    # Sort by similarity descending
    ranked = sorted(zip(chunks, scores), key=lambda x: x[1], reverse=True)

    # Take top_k
    top_results = [(item["text"], score) for item, score in ranked[:top_k]]
    return top_results


if __name__ == "__main__":
    # Quick test
    user_query = "What is this document about?"
    results = search(user_query, top_k=3)
    print(f"Top results for query: '{user_query}'\n")
    for text, score in results:
        print(f"[score={score:.3f}] {text[:100]}...")
