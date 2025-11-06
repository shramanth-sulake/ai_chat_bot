# app/search_db.py
import os
from typing import List, Tuple, Dict
from sqlalchemy import create_engine, text
from app.embeddings import get_embedding_model

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/ai_chat_db")
engine = create_engine(DATABASE_URL)


def _row_to_dict(r, cols):
    """
    Convert SQLAlchemy row to dictionary using row._mapping for safety.
    """
    try:
        mapping = r._mapping
        return {c: mapping.get(c) for c in cols}
    except Exception:
        # fallback if needed
        return {c: r[i] for i, c in enumerate(cols)}


def _vec_to_pg_literal(vec: List[float]) -> str:
    """
    Convert list of floats to pgvector literal string: '[0.1, 0.2, ...]'.
    This is required because we cast to vector later as (:q)::vector.
    """
    return "[" + ", ".join(repr(float(x)) for x in vec) + "]"


def search_db(query: str, top_k: int = 3) -> List[Tuple[Dict, float]]:
    """
    Search the DB for the most relevant chunks based on embedding similarity.
    Returns list of (chunk_dict, similarity_score).
    """
    model = get_embedding_model()
    q_vec = model.encode([query])[0].tolist()
    q_literal = _vec_to_pg_literal(q_vec)

    sql = text("""
        SELECT 
            id, doc, sheet, row_index, origin_cols, chunk_id, text, followups,
            embedding <-> (:q)::vector AS distance
        FROM chunks
        ORDER BY distance
        LIMIT :k
    """)

    with engine.connect() as conn:
        rows = conn.execute(sql, {"q": q_literal, "k": top_k}).fetchall()

    results = []
    cols = ["id", "doc", "sheet", "row_index", "origin_cols", "chunk_id", "text", "followups", "distance"]

    for r in rows:
        row_dict = _row_to_dict(r, cols)

        chunk = {
            "id": row_dict["id"],
            "doc": row_dict["doc"],
            "sheet": row_dict["sheet"],
            "row": row_dict["row_index"],
            "origin_cols": row_dict["origin_cols"],
            "chunk_id": row_dict["chunk_id"],
            "text": row_dict["text"],
            # ✅ followups stored directly as a single STRING
            "followups": row_dict.get("followups")  # <-- No JSON loading. No list. Just string.
        }

        # Convert pgvector distance to similarity score 0–1
        distance = float(row_dict["distance"])
        score = 1.0 / (1.0 + distance)

        results.append((chunk, score))

    return results
