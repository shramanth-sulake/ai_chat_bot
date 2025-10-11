import numpy as np
from app.embeddings import load_embeddings, get_embedding_model
import json

def cosine(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-10))

def main():
    query = input("Enter the exact query you used: ").strip()
    print("Loading chunks + vectors...")
    chunks, embeddings = load_embeddings()
    print("Chunks:", len(chunks), "Embeddings shape:", embeddings.shape)

    model = get_embedding_model()
    print("Encoding query...")
    qv = model.encode([query])[0]
    print("Query vector shape:", qv.shape)

    # compute scores
    scores = [cosine(qv, emb) for emb in embeddings]
    ranked = sorted(list(enumerate(scores)), key=lambda x: x[1], reverse=True)

    print("\nTop 5 matches (index, score):")
    for idx, score in ranked[:5]:
        text = chunks[idx]["text"]
        print(f"[{idx}] score={score:.4f}")
        print("  Text (first 200 chars):", text[:200].replace("\n"," "))
        print()

    # Show diagnostics for best and worst
    best_idx, best_score = ranked[0]
    worst_idx, worst_score = ranked[-1]
    print("Best index/norms:")
    print(" best_idx:", best_idx, "best_score:", best_score)
    print("  ||q||:", np.linalg.norm(qv), "||best_emb||:", np.linalg.norm(embeddings[best_idx]))
    print("Worst index/norms:")
    print(" worst_idx:", worst_idx, "worst_score:", worst_score)
    print("  ||worst_emb||:", np.linalg.norm(embeddings[worst_idx]))

if __name__ == "__main__":
    main()
