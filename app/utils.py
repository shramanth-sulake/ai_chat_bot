# app/utils.py
"""
Small utilities: in-memory LRU cache (simple) and a helper to compute confidence.
This cache is process-local and intended for dev. Replace with Redis/DB for production.
"""

from collections import OrderedDict
from typing import Any, Tuple

# Simple LRU cache class (fixed capacity)
class SimpleLRUCache:
    def __init__(self, capacity: int = 1024):
        self.capacity = capacity
        self._store = OrderedDict()

    def get(self, key: str):
        if key not in self._store:
            return None
        # move to end = most recently used
        self._store.move_to_end(key)
        return self._store[key]

    def set(self, key: str, value: Any):
        if key in self._store:
            self._store.move_to_end(key)
        self._store[key] = value
        if len(self._store) > self.capacity:
            # pop least recently used
            self._store.popitem(last=False)

    def clear(self):
        self._store.clear()

# Single cache instance you can import
query_response_cache = SimpleLRUCache(capacity=500)

def make_cache_key(user_id: str, question: str) -> str:
    """
    Normalize a question into a cache key. Keep it simple for now.
    """
    return f"{user_id}::{question.strip().lower()}"

def compute_confidence_from_scores(similarity_scores):
    """
    Given a list of similarity scores (descending), produce a confidence value 0..1.
    Simple heuristic:
      - if no scores -> 0.0
      - confidence = top_score (clamped)
      - if secondaries add support, slightly boost confidence
    """
    if not similarity_scores:
        return 0.0
    top = similarity_scores[0]
    # If multiple supporting chunks, increase a bit
    support = 0.0
    if len(similarity_scores) > 1:
        support = sum(similarity_scores[1: min(4, len(similarity_scores))]) / (len(similarity_scores)-1)
    # weight top more heavily
    confidence = 0.8 * top + 0.2 * support
    # clamp 0..1
    return max(0.0, min(1.0, confidence))
