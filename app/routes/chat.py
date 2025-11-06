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
    follow_up: Optional[str] = None  # Single most relevant followup (text)
    followups: List[Dict[str, Any]] = []  # List of all relevant followups (objects with text & score)
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

    # 3) Retrieve top chunks + similarity scores
    results = search(req.question, top_k=req.top_k)  # returns [(chunk_dict, score), ...]
    if not results:
        return ChatResponse(
            answer="I don't have specific information about that topic. However, I can tell you about our services like CX audits, website migrations, branding, or digital marketing. Which would you like to know more about?",
            confidence=0.0, 
            sources=[],
            follow_up="Would you like to learn about our core services?",
            followups=[
                {"text": "Can you tell me about your CX audit service?", "score": 0.8},
                {"text": "What website migration services do you offer?", "score": 0.75},
                {"text": "What branding services do you provide?", "score": 0.7},
                {"text": "How can you help with digital marketing?", "score": 0.68}
            ]
        )

    # 4) Extract texts, scores, and sources
    texts = [r[0]["text"] for r in results]
    scores = [r[1] for r in results]
    sources = [
        f"{r[0]['doc']} | {r[0]['sheet']} | row:{r[0]['row']} | chunk:{r[0]['chunk_id']}"
        for r in results
    ]

    # 5) Compute confidence
    confidence = compute_confidence_from_scores(scores)

    # 6) Get followups
    relevant_followups = followup_manager.find_relevant_followups(
        question=req.question,
        chunks=results,
        max_followups=3,
        similarity_threshold=0.5 if confidence >= CONFIDENCE_THRESHOLD else 0.3
    )
    
    # 7) Handle low-confidence cases
    if confidence < CONFIDENCE_THRESHOLD:
        # Use first followup text if available, otherwise use default message
        if relevant_followups:
            followup_text = relevant_followups[0].get("text")
        else:
            followup_text = "I couldn't find a confident answer — can you provide more details or rephrase?"

        resp = ChatResponse(
            answer=None,
            confidence=confidence,
            sources=sources[:1],  # Only include the top source
            follow_up=followup_text,
            followups=relevant_followups,
            redacted=False
        )
        query_response_cache.set(cache_key, resp.dict())
        return resp

    # 8) Generate answer via LLM
    answer = generate_answer(req.question, texts)

    # 9) Handle disallowed content
    if is_disallowed(answer):
        resp = ChatResponse(
            answer="I cannot provide that information.",
            confidence=0.0,
            sources=[],
            follow_up=None,
            followups=[],
            redacted=False
        )
        query_response_cache.set(cache_key, resp.dict())
        return resp

    # 10) Handle redaction
    redacted_answer, had_redaction = redact_text(answer)

    # 11) Build final response
    try:
        resp = ChatResponse(
            answer=redacted_answer if redacted_answer else None,
            confidence=float(confidence),
            sources=sources[:5],  # Limit sources to avoid overflow
            follow_up=(relevant_followups[0].get("text") if relevant_followups else None),
            followups=[f for f in relevant_followups if isinstance(f, dict) and isinstance(f.get("text"), str)][:3],
            redacted=bool(had_redaction)
        )
    except Exception as e:
        # Fallback to minimal response if serialization fails
        resp = ChatResponse(
            answer="An error occurred while processing the response",
            confidence=0.0,
            sources=[],
            follow_up=None,
            followups=[],
            redacted=False
        )

    # 12) Cache and return
    query_response_cache.set(cache_key, resp.dict())
    return resp
