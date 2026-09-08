"""Safe public error metadata shared by HTTP endpoints."""

from __future__ import annotations

import logging
import uuid

try:
    from flask import current_app, has_app_context
except ImportError:  # pragma: no cover
    current_app = None

    def has_app_context():
        return False


LOGGER = logging.getLogger(__name__)


def log_public_exception(exc: BaseException, *, code: str = "internal_error") -> dict:
    correlation_id = uuid.uuid4().hex
    logger = current_app.logger if has_app_context() else LOGGER
    logger.exception(
        "HTTP request failed correlation_id=%s code=%s",
        correlation_id,
        code,
        exc_info=exc,
    )
    return {
        "code": code,
        "message": "Não foi possível concluir a solicitação.",
        "correlation_id": correlation_id,
    }
