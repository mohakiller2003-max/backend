import logging
import time

import httpx

from app.core.config import settings
from app.db.models import Order
from app.utils.phone import snap_hash_phone

logger = logging.getLogger(__name__)

SNAP_CAPI_URL = "https://tr.snapchat.com/v2/conversion"


async def send_purchase_event(order: Order) -> bool:
    """Send PURCHASE server-side event to Snapchat Conversions API."""
    if not settings.SNAP_PIXEL_ID or not settings.SNAP_ACCESS_TOKEN:
        logger.info("Snapchat CAPI not configured, skipping.")
        return False

    phone_hash = snap_hash_phone(order.phone_e164)

    items = [
        {"id": item.product_id, "quantity": item.quantity}
        for item in order.items
        if item.unit_context == "bundle"
    ]

    payload = {
        "pixel_id": settings.SNAP_PIXEL_ID,
        "timestamp": int(time.time() * 1000),
        "event_type": "PURCHASE",
        "event_conversion_type": "WEB",
        "event_source_url": order.landing_page or settings.FRONTEND_BASE_URL,
        "user_agent": order.user_agent or "",
        "ip_address": order.client_ip or "",
        "phone_number": phone_hash,
        "price": float(order.total_aed),
        "currency": "AED",
        "transaction_id": order.order_number,
        "client_dedup_id": order.purchase_event_id or str(order.id),
        "snap_click_id": order.sc_click_id or "",
        "item_ids": [i["id"] for i in items],
        "number_items": sum(i["quantity"] for i in items),
    }

    headers = {
        "Authorization": f"Bearer {settings.SNAP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(SNAP_CAPI_URL, headers=headers, json=payload)
            if response.status_code in (200, 204):
                logger.info("Snap CAPI purchase sent order=%s", order.order_number)
                return True
            logger.warning(
                "Snap CAPI non-200 order=%s status=%s body=%s",
                order.order_number,
                response.status_code,
                response.text[:300],
            )
            return False
    except Exception as exc:
        logger.error("Snap CAPI error order=%s error=%s", order.order_number, str(exc))
        return False
