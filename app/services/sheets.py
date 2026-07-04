import json
import logging
import re
from datetime import datetime, timedelta, timezone

import httpx

from app.core.config import PRODUCT_CATALOG, settings
from app.db.models import Order

logger = logging.getLogger(__name__)

UAE_TZ = timezone(timedelta(hours=4))
REDIRECT_STATUS = {301, 302, 303, 307, 308}


def _parse_apps_script_response(text: str) -> dict | None:
    cleaned = text.strip()
    if cleaned.startswith(")]}'"):
        cleaned = cleaned[4:].strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r'\{[^{}]*"ok"\s*:\s*true[^{}]*\}', cleaned)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
        return None


def _response_is_ok(response: httpx.Response) -> bool:
    body = _parse_apps_script_response(response.text)
    if body and body.get("ok") is True:
        return True
    return '"ok":true' in response.text.replace(" ", "") or '"ok": true' in response.text


async def _send_to_apps_script(
    client: httpx.AsyncClient,
    base_url: str,
    payload: dict[str, object],
) -> tuple[bool, str]:
    """
    Google Apps Script web apps:
    - POST form → doPost runs → 302 to echo URL
    - Echo URL accepts GET only → read JSON result there
    """
    form = {k: "" if v is None else str(v) for k, v in payload.items()}
    url = base_url.rstrip("/")
    if settings.SHEETS_WEBHOOK_SECRET:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}secret={settings.SHEETS_WEBHOOK_SECRET}"

    post_response = await client.post(url, json=form, follow_redirects=False)

    if post_response.status_code in REDIRECT_STATUS:
        location = post_response.headers.get("location")
        if not location:
            return False, f"redirect without location (post={post_response.status_code})"
        get_response = await client.get(location, follow_redirects=True)
        if _response_is_ok(get_response):
            return True, "ok"
        return False, f"redirect GET status={get_response.status_code} body={get_response.text[:200]}"

    if post_response.status_code == 200 and _response_is_ok(post_response):
        return True, "ok"

    return False, f"post status={post_response.status_code} body={post_response.text[:200]}"


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
    """Forward order to Google Sheets. Never raises."""
    if not settings.SHEETS_WEBHOOK_URL:
        logger.warning("SHEETS_WEBHOOK_URL not configured, skipping sheet webhook.")
        return False

    if not order.items:
        logger.warning("Sheet webhook skipped order=%s — no order items loaded", order.order_number)
        return False

    payload = {
        "webhook_secret": settings.SHEETS_WEBHOOK_SECRET,
        **_build_sheet_fields(order),
    }

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(20.0, connect=8.0),
            follow_redirects=False,
        ) as client:
            ok, detail = await _send_to_apps_script(
                client,
                settings.SHEETS_WEBHOOK_URL,
                payload,
            )
            if ok:
                logger.info("Sheet webhook success order=%s", order.order_number)
                return True
            logger.warning("Sheet webhook failed order=%s detail=%s", order.order_number, detail)
            return False
    except Exception as exc:
        logger.error("Sheet webhook error order=%s error=%s", order.order_number, str(exc) or type(exc).__name__)
        return False
