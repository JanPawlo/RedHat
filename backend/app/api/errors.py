import logging

from fastapi import HTTPException, status

from app.const.auth import AUTH_SCHEME
from app.const.llm_limits import MODEL_BUSY_RETRY_AFTER_SECONDS, RETRY_AFTER_HEADER
from app.const.messages import (
    LLM_RATE_LIMITED_LOG,
    MODEL_BUSY,
    MODEL_CALL_FAILED_LOG,
    MODEL_ENDPOINT_UNAVAILABLE,
    NOT_AUTHENTICATED,
)

logger = logging.getLogger(__name__)


def unauthorized(detail: str = NOT_AUTHENTICATED) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": AUTH_SCHEME},
    )


def forbidden(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def conflict(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def model_unavailable(error: Exception) -> HTTPException:
    logger.error(MODEL_CALL_FAILED_LOG, exc_info=error)
    return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=MODEL_ENDPOINT_UNAVAILABLE)


def model_busy() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=MODEL_BUSY,
        headers={RETRY_AFTER_HEADER: str(MODEL_BUSY_RETRY_AFTER_SECONDS)},
    )


def too_many_requests(user_key: str, detail: str, retry_after: int) -> HTTPException:
    logger.info(LLM_RATE_LIMITED_LOG, user_key, detail)
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=detail,
        headers={RETRY_AFTER_HEADER: str(retry_after)},
    )
