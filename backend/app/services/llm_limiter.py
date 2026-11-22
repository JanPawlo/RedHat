"""
Protects the single-GPU model from overload (memory/decisions/bonusy.md, "Model load limits").

Two levels:
- **question** (`limiter.question(user_key)`): one question in progress per user and a few per minute (429).
  A question is everything one answer needs: a what-if with engine tools is 3 model calls but 1 question.
- **call** (`limiter.call(background)`): every HTTP call to the model takes one of the global slots.
  People wait at most `LLM_QUEUE_WAIT_SECONDS`, then get "model busy" (503). Card generation runs in the
  background lane: it waits much longer and never takes more than `LLM_BACKGROUND_MAX_CONCURRENT_CALLS`
  slots, so a slot stays free for someone asking a question while the deck is being written.
"""
import asyncio
import math
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from typing import AsyncIterator, Deque, Dict, Optional, Set

from app.const.llm_limits import (
    LLM_BACKGROUND_MAX_CONCURRENT_CALLS,
    LLM_BACKGROUND_QUEUE_WAIT_SECONDS,
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
        background_max_concurrent: int = LLM_BACKGROUND_MAX_CONCURRENT_CALLS,
        background_wait_seconds: float = LLM_BACKGROUND_QUEUE_WAIT_SECONDS,
    ):
        self.max_concurrent = max_concurrent
        self.queue_wait_seconds = queue_wait_seconds
        self.per_minute = per_minute
        self.window_seconds = window_seconds
        self.background_wait_seconds = background_wait_seconds
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._background = asyncio.Semaphore(max(1, min(background_max_concurrent, max_concurrent)))
        self._in_flight: Set[str] = set()
        self._recent: Dict[str, Deque[float]] = defaultdict(deque)

    @asynccontextmanager
    async def question(self, user_key: Optional[str]) -> AsyncIterator[None]:
        """One question of one user (any number of model calls inside); `RateLimitedError` (429) when not allowed."""
        if user_key is None:
            yield
            return

        self._claim_user(user_key)
        try:
            yield
        finally:
            self._in_flight.discard(user_key)

    @asynccontextmanager
    async def call(self, background: bool = False) -> AsyncIterator[None]:
        """One HTTP call to the model; `SlotTimeoutError` (503) when no slot frees up in time."""
        if not background:
            await self._acquire(self._semaphore, self.queue_wait_seconds)
            try:
                yield
            finally:
                self._semaphore.release()
            return

        await self._acquire(self._background, self.background_wait_seconds)
        try:
            await self._acquire(self._semaphore, self.background_wait_seconds)
            try:
                yield
            finally:
                self._semaphore.release()
        finally:
            self._background.release()

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

    @staticmethod
    async def _acquire(semaphore: asyncio.Semaphore, timeout: float) -> None:
        try:
            await asyncio.wait_for(semaphore.acquire(), timeout=timeout)
        except asyncio.TimeoutError as exc:
            raise SlotTimeoutError() from exc


limiter = LlmLimiter()


def reset_limiter() -> None:
    """Fresh limits (tests, or after changing the constants at runtime)."""
    global limiter
    limiter = LlmLimiter()


def get_limiter() -> LlmLimiter:
    return limiter
