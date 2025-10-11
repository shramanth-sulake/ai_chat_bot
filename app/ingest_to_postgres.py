# app/ingest_to_postgres.py
import os
from typing import List, Dict
from datetime import datetime
import json

from sqlalchemy import create_engine, Column, Integer, Text, TIMESTAMP
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector
from app.embeddings import chunk_document, get_embedding_model

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/ai_chat_db")

Base = declarative_base()

class Chunk(Base):
    __tablename__ = "chunks"
    id = Column(Integer, primary_key=True)
    doc = Column(Text)
    sheet = Column(Text)
    row_index = Column(Integer)
    origin_cols = Column(Text)
    chunk_id = Column(Integer)
    text = Column(Text)
    embedding = Column(Vector(384))
    followups = Column(JSONB, default=list)   # store list of follow-up questions for this chunk
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

def connect_db():
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return engine, Session

def ingest_passages_to_db(passages: List[Dict], chunk_size=500, chunk_overlap=50):
    """
    passages: list of dicts with keys: doc, sheet, row, col, text, followups (optional)
    followups should be a list of strings or an empty list.
    """
    engine, Session = connect_db()
    session = Session()
    model = get_embedding_model()

    inserted = 0
    try:
        for p in passages:
            text_full = p["text"]
            subchunks = chunk_document(text_full, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
            if not subchunks:
                continue
            vectors = model.encode(subchunks, show_progress_bar=False)
            # extract followups for this passage (if any)
            passage_followups = p.get("followups", []) or []
            # We'll attach the same passage_followups to every subchunk created from this passage.
            for ci, (ctext, vec) in enumerate(zip(subchunks, vectors)):
                chunk = Chunk(
                    doc=p.get("doc"),
                    sheet=p.get("sheet"),
                    row_index=p.get("row"),
                    origin_cols=p.get("col"),
                    chunk_id=ci,
                    text=ctext,
                    embedding=list(map(float, vec)),
                    followups=passage_followups
                )
                session.add(chunk)
                inserted += 1
        session.commit()
        print(f"[ingest_to_postgres] Inserted {inserted} chunks.")
    except Exception as e:
        session.rollback()
        raise
    finally:
        session.close()
