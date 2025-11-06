# app/search_db.py  (PATCH - use string cast to vector)
import os
from typing import List, Tuple, Dict
import json
from sqlalchemy import create_engine, text
from app.embeddings import get_embedding_model

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/ai_chat_db")
engine = create_engine(DATABASE_URL)

def _row_to_dict(r, cols):
    try:
        mapping = r._mapping
        return {c: mapping.get(c) for c in cols}
    except Exception:
        return {c: r[i] for i, c in enumerate(cols)}

def _vec_to_pg_literal(vec: List[float]) -> str:
    """
    Convert Python list of floats to Postgres/pgvector literal string: '[0.1, 0.2, ...]'.
    We'll send that string as a bind parameter and cast it to vector in the SQL: :q::vector
    """
    return "[" + ", ".join(repr(float(x)) for x in vec) + "]"

def search_db(query: str, top_k: int = 3) -> List[Tuple[Dict, float]]:
    model = get_embedding_model()
    q_vec = model.encode([query])[0].tolist()

    # Create a string literal for PG vector and cast in SQL
    q_literal = _vec_to_pg_literal(q_vec)

    sql = text("""
        SELECT id, doc, sheet, row_index, origin_cols, chunk_id, text, followups, embedding <-> (:q)::vector AS distance
        FROM chunks
        ORDER BY distance
        LIMIT :k
    """)

    # Bind q as string (Postgres will cast it to vector because of ::vector)
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
            # parse followups stored as JSON/text in the DB; normalize to list
            "followups": []  # Initialize empty list
        }
        # Safely try to parse followups
        try:
            if row_dict.get("followups"):
                followups = json.loads(row_dict["followups"])
                if isinstance(followups, list):
                    chunk["followups"] = followups
        except (json.JSONDecodeError, TypeError):
            pass  # Keep empty list on error
            
        distance = row_dict["distance"]
        score = 1.0 / (1.0 + float(distance))
        results.append((chunk, score))
    return results
