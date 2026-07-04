import logging
import re
from datetime import datetime, timedelta, timezone

import httpx

from app.core.config import PRODUCT_CATALOG, settings
from app.db.models import Order

logger = logging.getLogger(__name__)

UAE_TZ = timezone(timedelta(hours=4))
REDIRECT_STATUS = {301, 302, 303, 307, 308}


async def _post_apps_script(
    client: httpx.AsyncClient,
    url: str,
    payload: dict[str, object],
) -> httpx.Response:
    """
    Google Apps Script /exec URLs respond with HTTP 302.
    httpx follow_redirects converts POST→GET and drops the JSON body, so the
    script receives {} and returns UNAUTHORIZED. Re-POST manually to Location.
    """
    current_url = url
    for _ in range(5):
        response = await client.post(current_url, json=payload, follow_redirects=False)
        if response.status_code not in REDIRECT_STATUS:
            return response
        location = response.headers.get("location")
        if not location:
            return response
        current_url = location
    return response


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
            timeout=settings.ORDER_WEBHOOK_TIMEOUT_SECONDS,
            follow_redirects=False,
        ) as client:
            url = settings.SHEETS_WEBHOOK_URL
            if settings.SHEETS_WEBHOOK_SECRET:
                sep = "&" if "?" in url else "?"
                url = f"{url}{sep}secret={settings.SHEETS_WEBHOOK_SECRET}"
            response = await _post_apps_script(client, url, payload)
            if response.status_code == 200:
                try:
                    body = response.json()
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
                    return False
            logger.warning(
                "Sheet webhook non-200 order=%s status=%s body=%s",
                order.order_number,
                response.status_code,
                response.text[:300],
            )
            return False
    except Exception as exc:
        logger.error("Sheet webhook error order=%s error=%s", order.order_number, str(exc))
        return False
