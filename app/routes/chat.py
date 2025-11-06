# app/routes/chat.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from app.search_db import search_db as search
from app.llm_manager import generate_answer
from app.utils import make_cache_key, query_response_cache, compute_confidence_from_scores
from app.filters import redact_text, is_disallowed
from app.followup_manager import followup_manager

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/")
def welcome_message():
    """Return initial greeting when chat starts."""
    return {
        "answer": "Hi there! I'm Chatty, how can I assist you today?",
        "confidence": 1.0,
        "sources": [],
        "cached": False,
        "follow_up": None,
        "followups": [],
        "redacted": False
    }


# -------------------------------
# Pydantic Models
# -------------------------------
class ChatRequest(BaseModel):
    user_id: str
    question: str
    top_k: Optional[int] = 3


class ChatResponse(BaseModel):
    answer: Optional[str] = None
    confidence: float = 0.0
    sources: List[str] = []
    cached: bool = False
    follow_up: Optional[str] = None
    followups: List[Dict[str, Any]] = []
    redacted: bool = False


CONFIDENCE_THRESHOLD = 0.35


# -------------------------------
# Chat Endpoint
# -------------------------------
@router.post("/", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="question is empty")

    # 1) Check Cache
    cache_key = make_cache_key(req.user_id, req.question)
    cached = query_response_cache.get(cache_key)
    if cached:
        resp = ChatResponse(**cached)
        resp.cached = True
        return resp

    # 2) Retrieve Top Chunks
    results = search(req.question, top_k=req.top_k)
    if not results:
        return ChatResponse(
            answer="I don't have enough information on that yet.",
            confidence=0.0,
            sources=[],
            follow_up="Would you like to ask something else?",
            followups=[]
        )

    texts = [r[0]["text"] for r in results]
    scores = [r[1] for r in results]
    sources = [
        f"{r[0]['doc']} | {r[0]['sheet']} | row:{r[0]['row']} | chunk:{r[0]['chunk_id']}"
        for r in results
    ]

    # 3) Confidence
    confidence = compute_confidence_from_scores(scores)

    # 4) Derive followups from chunks
    relevant_followups = []
    for chunk, score in results:
        if "followups" in chunk and chunk["followups"]:
            # Normalize: ensure always list of strings
            if isinstance(chunk["followups"], list):
                for f in chunk["followups"]:
                    if isinstance(f, str):
                        relevant_followups.append({"text": f, "score": score})
            elif isinstance(chunk["followups"], str):
                relevant_followups.append({"text": chunk["followups"].strip(), "score": score})

    # Sort follow-ups by similarity score descending
    relevant_followups.sort(key=lambda x: x["score"], reverse=True)
    # Pick the top one if exists
    follow_up = (
        relevant_followups[0]["text"]
        if relevant_followups and isinstance(relevant_followups[0]["text"], str)
        else None
    )

    # 5) Low Confidence -> Ask follow-up instead of answering
    if confidence < CONFIDENCE_THRESHOLD:
        resp = ChatResponse(
            answer=None,
            confidence=confidence,
            sources=sources[:1],
            follow_up=follow_up,
            followups=relevant_followups[:3],
            redacted=False
        )
        query_response_cache.set(cache_key, resp.dict())
        return resp

    # 6) Generate Answer from LLM
    answer = generate_answer(req.question, texts)

    if is_disallowed(answer):
        return ChatResponse(
            answer="I cannot provide that information.",
            confidence=0.0,
            sources=[],
            follow_up=None,
            followups=[],
            redacted=False
        )

    redacted_answer, had_redaction = redact_text(answer)

    # 7) Final Successful Response
    resp = ChatResponse(
        answer=redacted_answer or None,
        confidence=float(confidence),
        sources=sources[:5],
        follow_up=follow_up,
        followups=relevant_followups[:3],
        redacted=bool(had_redaction)
    )

    query_response_cache.set(cache_key, resp.dict())
    return resp
