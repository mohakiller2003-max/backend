import json
import logging
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx

from app.core.config import PRODUCT_CATALOG, settings
from app.db.models import Order

logger = logging.getLogger(__name__)

UAE_TZ = timezone(timedelta(hours=4))


def _parse_apps_script_response(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith(")]}'"):
        cleaned = cleaned[4:].strip()
    return json.loads(cleaned)


async def _call_apps_script(
    client: httpx.AsyncClient,
    base_url: str,
    payload: dict[str, object],
) -> httpx.Response:
    """
    Google Apps Script web apps are most reliable over GET.
    Redirect chain stays GET end-to-end (no 405 on echo URL).
    """
    params = {k: "" if v is None else str(v) for k, v in payload.items()}
    if settings.SHEETS_WEBHOOK_SECRET:
        params["secret"] = settings.SHEETS_WEBHOOK_SECRET
    query = urlencode(params)
    url = f"{base_url.rstrip('/')}?{query}"
    return await client.get(url, follow_redirects=True)

def _format_sheet_date(order: Order) -> str:
    created = order.created_at or datetime.utcnow()
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return created.astimezone(UAE_TZ).strftime("%d/%m/%Y")


def _format_phone_digits(phone_e164: str) -> str:
    digits = re.sub(r"\D", "", phone_e164 or "")
    if digits.startswith("00"):
        digits = digits[2:]
    return digits


def _build_sheet_fields(order: Order) -> dict[str, str | float]:
    product_names: list[str] = []
    skus: list[str] = []
    quantities: list[str] = []

    for item in order.items:
        catalog = PRODUCT_CATALOG.get(item.product_id, {})
        product_names.append(item.product_name_ar or catalog.get("name_ar", item.product_id))
        skus.append(catalog.get("sku", item.product_id))
        quantities.append(str(item.quantity))

    return {
        "date": _format_sheet_date(order),
        "order_id": order.order_number,
        "country": "UAE",
        "name": order.customer_name,
        "phone": _format_phone_digits(order.phone_e164 or order.phone_raw),
        "product": "/".join(product_names),
        "sku": "/".join(skus),
        "quantity": "/".join(quantities),
        "total_price": float(order.total_aed),
        "currency": "AED",
        "status": "",
    }


async def send_order_to_sheet(order: Order) -> bool:
    """
    Forward order to Google Sheets via Apps Script webhook.
    Returns True on success, False on failure.
    Never raises — sheet failure must not break the order flow.
    """
    if not settings.SHEETS_WEBHOOK_URL:
        logger.warning("SHEETS_WEBHOOK_URL not configured, skipping sheet webhook.")
        return False

    sheet_fields = _build_sheet_fields(order)
    payload = {
        "webhook_secret": settings.SHEETS_WEBHOOK_SECRET,
        **sheet_fields,
    }

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(settings.ORDER_WEBHOOK_TIMEOUT_SECONDS, connect=5.0),
            follow_redirects=True,
        ) as client:
            response = await _call_apps_script(
                client,
                settings.SHEETS_WEBHOOK_URL,
                payload,
            )
            if response.status_code == 200:
                try:
                    body = _parse_apps_script_response(response.text)
                    if body.get("ok") is True:
                        logger.info("Sheet webhook success order=%s", order.order_number)
                        return True
                    logger.warning(
                        "Sheet webhook rejected order=%s error=%s body=%s",
                        order.order_number,
                        body.get("error"),
                        response.text[:300],
                    )
                    return False
                except Exception:
                    logger.warning(
                        "Sheet webhook invalid JSON order=%s body=%s",
                        order.order_number,
                        response.text[:300],
                    )
                    return False            logger.warning(
                "Sheet webhook non-200 order=%s status=%s body=%s",
                order.order_number,
                response.status_code,
                response.text[:300],
            )
            return False
    except Exception as exc:
        logger.error("Sheet webhook error order=%s error=%s", order.order_number, str(exc))
        return False
