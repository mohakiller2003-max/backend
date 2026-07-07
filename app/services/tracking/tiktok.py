import logging
import time

import httpx

from app.core.config import settings
from app.db.models import Order
from app.services.tracking.capi_log import log_capi_error, log_capi_fail, log_capi_ok, log_capi_send, log_capi_skip
from app.utils.phone import tiktok_hash_phone

logger = logging.getLogger(__name__)

TIKTOK_EVENTS_URL = "https://business-api.tiktok.com/open_api/v1.3/event/track/"


async def send_purchase_event(order: Order) -> bool:
    """Send CompletePayment server-side event to TikTok Events API v1.3 (hashed phone on server)."""
    if not settings.TIKTOK_PIXEL_ID or not settings.TIKTOK_ACCESS_TOKEN:
        log_capi_skip("TikTok", "TIKTOK_PIXEL_ID or TIKTOK_ACCESS_TOKEN not set")
        return False

    event_id = order.purchase_event_id or str(order.id)
    log_capi_send("TikTok", order.order_number, event_id)

    phone_hash = tiktok_hash_phone(order.phone_e164)

    content_list = [
        {
            "content_id": item.product_id,
            "content_type": "product",
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
        "event_id": event_id,
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
            "content_type": "product",
            "order_id": order.order_number,
        },
    }

    if settings.TIKTOK_TEST_EVENT_CODE:
        event["test_event_code"] = settings.TIKTOK_TEST_EVENT_CODE

    payload = {
        "event_source": "web",
        "event_source_id": settings.TIKTOK_PIXEL_ID,
        "data": [event],
    }

    headers = {
        "Access-Token": settings.TIKTOK_ACCESS_TOKEN,
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(TIKTOK_EVENTS_URL, headers=headers, json=payload)
            try:
                body = response.json()
            except ValueError:
                body = {"raw": response.text[:500]}

            if response.status_code == 200 and isinstance(body, dict) and body.get("code") == 0:
                log_capi_ok("TikTok", order.order_number, event_id, response.status_code, body)
                return True

            log_capi_fail("TikTok", order.order_number, event_id, response.status_code, body)
            return False
    except Exception as exc:
        log_capi_error("TikTok", order.order_number, event_id, exc)
        return False
