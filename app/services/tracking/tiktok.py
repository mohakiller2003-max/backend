import json
import logging
import time
from typing import Optional

import httpx

from app.core.config import settings
from app.db.models import Order
from app.utils.phone import tiktok_hash_phone

logger = logging.getLogger(__name__)

TIKTOK_EVENTS_URL = "https://business-api.tiktok.com/open_api/v1.3/event/track/"


async def send_purchase_event(order: Order) -> bool:
    """Send CompletePayment server-side event to TikTok Events API."""
    if not settings.TIKTOK_PIXEL_ID or not settings.TIKTOK_ACCESS_TOKEN:
        logger.info("TikTok Events API not configured, skipping.")
        return False

    phone_hash = tiktok_hash_phone(order.phone_e164)

    content_list = [
        {
            "content_id": item.product_id,
            "content_name": item.product_name_en,
            "quantity": item.quantity,
            "price": float(item.bundle_price_aed),
        }
        for item in order.items
        if item.unit_context == "bundle"
    ]

    event = {
        "event": "CompletePayment",
        "event_time": int(time.time()),
        "event_id": order.purchase_event_id or str(order.id),
        "page": {
            "url": order.landing_page or settings.FRONTEND_BASE_URL,
            "referrer": order.referrer or "",
        },
        "user": {
            "phone": phone_hash,
            "ip": order.client_ip or "",
            "user_agent": order.user_agent or "",
            "ttclid": order.ttclid or "",
        },
        "properties": {
            "currency": "AED",
            "value": float(order.total_aed),
            "contents": content_list,
            "order_id": order.order_number,
        },
    }

    if settings.TIKTOK_TEST_EVENT_CODE:
        event["test_event_code"] = settings.TIKTOK_TEST_EVENT_CODE

    payload = {
        "pixel_code": settings.TIKTOK_PIXEL_ID,
        "event_source": "web",
        "partner_name": "Skinouva",
        "data": [event],
    }

    headers = {
        "Access-Token": settings.TIKTOK_ACCESS_TOKEN,
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(TIKTOK_EVENTS_URL, headers=headers, json=payload)
            if response.status_code == 200:
                logger.info("TikTok CAPI purchase sent order=%s", order.order_number)
                return True
            logger.warning(
                "TikTok CAPI non-200 order=%s status=%s body=%s",
                order.order_number,
                response.status_code,
                response.text[:300],
            )
            return False
    except Exception as exc:
        logger.error("TikTok CAPI error order=%s error=%s", order.order_number, str(exc))
        return False
