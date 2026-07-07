import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def _short_body(body: Any, limit: int = 500) -> str:
    if body is None:
        return ""
    if isinstance(body, (dict, list)):
        text = json.dumps(body, ensure_ascii=False, default=str)
    else:
        text = str(body)
    return text if len(text) <= limit else text[:limit] + "..."


def log_capi_skip(platform: str, reason: str) -> None:
    logger.info("[CAPI:%s] skipped — %s", platform, reason)


def log_capi_send(platform: str, order_number: str, event_id: str) -> None:
    logger.info("[CAPI:%s] sending order=%s event_id=%s", platform, order_number, event_id)


def log_capi_ok(platform: str, order_number: str, event_id: str, status_code: int, body: Any) -> None:
    logger.info(
        "[CAPI:%s] ok order=%s event_id=%s status=%s response=%s",
        platform,
        order_number,
        event_id,
        status_code,
        _short_body(body),
    )


def log_capi_fail(platform: str, order_number: str, event_id: str, status_code: int, body: Any) -> None:
    logger.warning(
        "[CAPI:%s] failed order=%s event_id=%s status=%s response=%s",
        platform,
        order_number,
        event_id,
        status_code,
        _short_body(body),
    )


def log_capi_error(platform: str, order_number: str, event_id: str, error: Exception) -> None:
    logger.error(
        "[CAPI:%s] error order=%s event_id=%s error=%s",
        platform,
        order_number,
        event_id,
        str(error),
        exc_info=True,
    )
