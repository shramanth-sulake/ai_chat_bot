# app/routes/chat.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from app.search_db import search_db as search
from app.llm_manager import generate_answer
from app.utils import make_cache_key, query_response_cache, compute_confidence_from_scores
from app.filters import redact_text, is_disallowed

router = APIRouter(prefix="/chat", tags=["chat"])

# -------------------------------
# Pydantic models
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
    redacted: bool = False

# -------------------------------
# Constants
# -------------------------------
CONFIDENCE_THRESHOLD = 0.35   # below this -> low confidence (adjust with real data)


# -------------------------------
# Chat endpoint
# -------------------------------
@router.post("/", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest):
    # 1) Input validation
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="question is empty")

    # 2) Cache check
    cache_key = make_cache_key(req.user_id, req.question)
    cached = query_response_cache.get(cache_key)
    if cached:
        resp = ChatResponse(**cached)
        resp.cached = True
        return resp

    # 3) Retrieve top chunks + similarity scores (🔁 modified section)
    results = search(req.question, top_k=req.top_k)  # returns [(chunk_dict, score), ...]
    if not results:
        return ChatResponse(answer="I don't know.", confidence=0.0, sources=[])

    # Extract texts, scores, and sources
    texts = [r[0]["text"] for r in results]
    scores = [r[1] for r in results]
    sources = [
        f"{r[0]['doc']} | {r[0]['sheet']} | row:{r[0]['row']} | chunk:{r[0]['chunk_id']}"
        for r in results
    ]

    # 4) Compute confidence
    confidence = compute_confidence_from_scores(scores)

    # 5) Handle low-confidence cases
    if confidence < CONFIDENCE_THRESHOLD:
        # Prefer author-provided follow-ups if present on the top chunk
        top_chunk = results[0][0]  # chunk metadata dict
        candidate_followup = None

        # top_chunk may contain a 'followups' field (list)
        if isinstance(top_chunk.get("followups"), (list, tuple)) and top_chunk.get("followups"):
            candidate_followup = top_chunk["followups"][0]  # pick the first follow-up
        else:
            # fallback: try to detect follow-up-like sentences in the chunk text (optional)
            candidate_followup = "I couldn't find a confident answer — can you provide more details or rephrase?"

        resp = ChatResponse(
            answer=None,
            confidence=confidence,
            sources=[f"{top_chunk.get('doc')} | {top_chunk.get('sheet')} | row:{top_chunk.get('row')} | chunk:{top_chunk.get('chunk_id')}"],
            follow_up=candidate_followup
        )
        query_response_cache.set(cache_key, resp.dict())
        return resp
   

    # 6) Generate answer via LLM
    answer = generate_answer(req.question, texts)

    # 7) Post-filtering and redaction
    redacted_flag = False

    if is_disallowed(answer):
        resp = ChatResponse(answer="I cannot provide that information.", confidence=0.0, sources=[])
        query_response_cache.set(cache_key, resp.dict())
        return resp

    redacted_answer, had_redaction = redact_text(answer)
    if had_redaction:
        redacted_flag = True

    # 8) Build final response (✅ now includes structured source info)
    resp = ChatResponse(
        answer=redacted_answer,
        confidence=confidence,
        sources=sources,  # replaced previews with actual doc/sheet/row/chunk info
        cached=False,
        redacted=redacted_flag
    )

    # 9) Cache and return
    query_response_cache.set(cache_key, resp.dict())
    return resp