"""
Short-lived cache of model explanations: the same facts, question and context (prompt, chat history) give the
same answer without another GPU call. Facts change with the data, so a changed card gets a new key.
"""
import hashlib
import json
import time
from collections import OrderedDict
from typing import Any, Dict, Optional, Tuple

from app.const.llm_limits import EXPLAIN_CACHE_MAX_ENTRIES, EXPLAIN_CACHE_TTL_SECONDS


class AnswerCache:
    def __init__(self, ttl_seconds: float = EXPLAIN_CACHE_TTL_SECONDS, max_entries: int = EXPLAIN_CACHE_MAX_ENTRIES):
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._entries: "OrderedDict[str, Tuple[float, str]]" = OrderedDict()

    @staticmethod
    def key(facts: Dict[str, Any], question: str, *context: Any) -> str:
        """`context` = everything else that changes the answer: the prompt or mode, the chat history, the card."""
        text = json.dumps([facts, " ".join(question.lower().split()), *context], sort_keys=True, default=str)
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def get(self, key: str) -> Optional[str]:
        entry = self._entries.get(key)
        if entry is None:
            return None

        stored_at, answer = entry
        if time.monotonic() - stored_at > self.ttl_seconds:
            del self._entries[key]
            return None

        self._entries.move_to_end(key)
        return answer

    def put(self, key: str, answer: str) -> None:
        self._entries[key] = (time.monotonic(), answer)
        self._entries.move_to_end(key)

        while len(self._entries) > self.max_entries:
            self._entries.popitem(last=False)

    def clear(self) -> None:
        self._entries.clear()


explain_cache = AnswerCache()
