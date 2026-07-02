import json
import logging
from datetime import datetime

import httpx

from app.core.config import settings
from app.db.models import Order

logger = logging.getLogger(__name__)


def _build_items_summary(order: Order) -> str:
    parts = []
    for item in order.items:
        name = item.product_name_en
        parts.append(f"{item.quantity}x {name} ({item.unit_context}) = {float(item.bundle_price_aed)} AED")
    return "; ".join(parts)


async def send_order_to_sheet(order: Order) -> bool:
    """
    Forward order to Google Sheets via Apps Script webhook.
    Returns True on success, False on failure.
    Never raises — sheet failure must not break the order flow.
    """
    if not settings.SHEETS_WEBHOOK_URL:
        logger.warning("SHEETS_WEBHOOK_URL not configured, skipping sheet webhook.")
        return False

    payload = {
        "webhook_secret": settings.SHEETS_WEBHOOK_SECRET,
        "created_at": order.created_at.isoformat() if order.created_at else datetime.utcnow().isoformat(),
        "order_number": order.order_number,
        "order_id": str(order.id),
        "status": order.status,
        "locale": order.locale,
        "customer_name": order.customer_name,
        "phone_raw": order.phone_raw,
        "phone_e164": order.phone_e164,
        "items_summary": _build_items_summary(order),
        "subtotal_aed": float(order.subtotal_aed),
        "upsell_total_aed": float(order.upsell_total_aed),
        "total_aed": float(order.total_aed),
        "currency": order.currency,
        "payment_method": order.payment_method,
        "utm_source": order.utm_source or "",
        "utm_medium": order.utm_medium or "",
        "utm_campaign": order.utm_campaign or "",
        "utm_content": order.utm_content or "",
        "utm_term": order.utm_term or "",
        "fbclid": order.fbclid or "",
        "ttclid": order.ttclid or "",
        "sc_click_id": order.sc_click_id or "",
        "landing_page": order.landing_page or "",
        "referrer": order.referrer or "",
        "purchase_event_id": order.purchase_event_id or "",
        "notes": "",
    }

    try:
        async with httpx.AsyncClient(timeout=settings.ORDER_WEBHOOK_TIMEOUT_SECONDS) as client:
            url = settings.SHEETS_WEBHOOK_URL
            if settings.SHEETS_WEBHOOK_SECRET:
                sep = "&" if "?" in url else "?"
                url = f"{url}{sep}secret={settings.SHEETS_WEBHOOK_SECRET}"
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                logger.info("Sheet webhook success order=%s", order.order_number)
                return True
            logger.warning(
                "Sheet webhook non-200 order=%s status=%s body=%s",
                order.order_number,
                response.status_code,
                response.text[:200],
            )
            return False
    except Exception as exc:
        logger.error("Sheet webhook error order=%s error=%s", order.order_number, str(exc))
        return False
