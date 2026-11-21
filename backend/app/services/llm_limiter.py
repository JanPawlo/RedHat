"""
Protects the single-GPU model from overload: a global limit of parallel calls with a short queue,
and per-user limits (one question in progress, a few per minute).
"""
import asyncio
import math
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from typing import AsyncIterator, Deque, Dict, Optional, Set

from app.const.llm_limits import (
    LLM_MAX_CONCURRENT_CALLS,
    LLM_QUEUE_WAIT_SECONDS,
    LLM_RATE_WINDOW_SECONDS,
    LLM_USER_REQUESTS_PER_MINUTE,
)
from app.const.messages import LLM_PREVIOUS_QUESTION_RUNNING, LLM_TOO_MANY_QUESTIONS


class SlotTimeoutError(Exception):
    """No free model slot within the queue wait."""


class RateLimitedError(Exception):
    """The user asked too much; `retry_after` is in whole seconds."""

    def __init__(self, message: str, retry_after: int):
        super().__init__(message)
        self.message = message
        self.retry_after = retry_after


class LlmLimiter:
    def __init__(
        self,
        max_concurrent: int = LLM_MAX_CONCURRENT_CALLS,
        queue_wait_seconds: float = LLM_QUEUE_WAIT_SECONDS,
        per_minute: int = LLM_USER_REQUESTS_PER_MINUTE,
        window_seconds: float = LLM_RATE_WINDOW_SECONDS,
    ):
        self.max_concurrent = max_concurrent
        self.queue_wait_seconds = queue_wait_seconds
        self.per_minute = per_minute
        self.window_seconds = window_seconds
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._in_flight: Set[str] = set()
        self._recent: Dict[str, Deque[float]] = defaultdict(deque)

    @asynccontextmanager
    async def slot(self, user_key: Optional[str] = None) -> AsyncIterator[None]:
        """One model call: per-user checks first (429), then a global slot or `SlotTimeoutError` (503)."""
        if user_key is not None:
            self._claim_user(user_key)

        try:
            await self._acquire_global()
            try:
                yield
            finally:
                self._semaphore.release()
        finally:
            if user_key is not None:
                self._in_flight.discard(user_key)

    def _claim_user(self, user_key: str) -> None:
        if user_key in self._in_flight:
            raise RateLimitedError(LLM_PREVIOUS_QUESTION_RUNNING, retry_after=1)

        now = time.monotonic()
        recent = self._recent[user_key]
        while recent and now - recent[0] >= self.window_seconds:
            recent.popleft()

        if len(recent) >= self.per_minute:
            wait = max(1, math.ceil(self.window_seconds - (now - recent[0])))
            raise RateLimitedError(LLM_TOO_MANY_QUESTIONS.format(seconds=wait), retry_after=wait)

        recent.append(now)
        self._in_flight.add(user_key)

    async def _acquire_global(self) -> None:
        try:
            await asyncio.wait_for(self._semaphore.acquire(), timeout=self.queue_wait_seconds)
        except asyncio.TimeoutError as exc:
            raise SlotTimeoutError() from exc


limiter = LlmLimiter()


def reset_limiter() -> None:
    """Fresh limits (tests, or after changing the constants at runtime)."""
    global limiter
    limiter = LlmLimiter()


def get_limiter() -> LlmLimiter:
    return limiter
