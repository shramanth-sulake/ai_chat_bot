# compare_embed_query.py
import numpy as np
from app.embeddings import get_embedding_model
import json
import os

# load chunk text directly from your saved chunks.json (so we compare the same chunk)
chunks_path = os.path.join("data", "embeddings", "chunks.json")
if not os.path.exists(chunks_path):
    raise SystemExit("chunks.json not found. Run ingest_sample.py first.")

with open(chunks_path, "r", encoding="utf-8") as f:
    chunks = json.load(f)

chunk_text = chunks[0]["text"]
query = "What is this about?"

model = get_embedding_model()
# compute both embeddings in the same session
chunk_vec = model.encode([chunk_text])[0]
query_vec = model.encode([query])[0]

# compute cosine (dot product if normalized)
def cosine(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))

print("Chunk text (preview):", chunk_text)
print("Query:", query)
print("chunk_vec[:8]:", chunk_vec[:8])
print("query_vec[:8]:", query_vec[:8])
print("||chunk||:", np.linalg.norm(chunk_vec))
print("||query||:", np.linalg.norm(query_vec))
print("Cosine similarity:", cosine(query_vec, chunk_vec))
