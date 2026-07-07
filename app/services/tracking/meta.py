import logging
import time
from typing import Optional

import httpx

from app.core.config import settings
from app.db.models import Order
from app.services.tracking.capi_log import log_capi_error, log_capi_fail, log_capi_ok, log_capi_send, log_capi_skip
from app.utils.phone import meta_hash_first_name, meta_hash_phone

logger = logging.getLogger(__name__)

META_CAPI_URL = "https://graph.facebook.com/v21.0/{pixel_id}/events"


async def send_purchase_event(
    order: Order,
    fbp: Optional[str] = None,
    fbc: Optional[str] = None,
) -> bool:
    """Send Purchase server-side event to Meta Conversions API (hashed PII on server)."""
    if not settings.META_PIXEL_ID or not settings.META_ACCESS_TOKEN:
        log_capi_skip("Meta", "META_PIXEL_ID or META_ACCESS_TOKEN not set")
        return False

    event_id = order.purchase_event_id or str(order.id)
    log_capi_send("Meta", order.order_number, event_id)

    phone_hash = meta_hash_phone(order.phone_e164)
    fn_hash = meta_hash_first_name(order.customer_name)

    user_data: dict = {
        "ph": [phone_hash],
        "client_ip_address": order.client_ip or "",
        "client_user_agent": order.user_agent or "",
    }
    if fn_hash:
        user_data["fn"] = [fn_hash]
    if fbp:
        user_data["fbp"] = fbp
    if fbc or order.fbclid:
        user_data["fbc"] = fbc or f"fb.1.{int(time.time() * 1000)}.{order.fbclid}"

    bundle_items = [item for item in order.items if item.unit_context == "bundle"]
    contents = [{"id": item.product_id, "quantity": item.quantity} for item in bundle_items]
    content_ids = [item.product_id for item in bundle_items]

    event = {
        "event_name": "Purchase",
        "event_time": int(time.time()),
        "event_id": event_id,
        "action_source": "website",
        "event_source_url": order.landing_page or settings.FRONTEND_BASE_URL,
        "user_data": user_data,
        "custom_data": {
            "currency": "AED",
            "value": float(order.total_aed),
            "contents": contents,
            "content_ids": content_ids,
            "content_type": "product",
            "num_items": sum(item.quantity for item in bundle_items),
            "order_id": order.order_number,
        },
    }

    payload: dict = {"data": [event]}
    if settings.META_TEST_EVENT_CODE:
        payload["test_event_code"] = settings.META_TEST_EVENT_CODE

    url = META_CAPI_URL.format(pixel_id=settings.META_PIXEL_ID)
    params = {"access_token": settings.META_ACCESS_TOKEN}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, params=params, json=payload)
            body: dict | list | str
            try:
                body = response.json()
            except ValueError:
                body = response.text[:500]

            if response.status_code == 200 and isinstance(body, dict):
                events_received = body.get("events_received", 0)
                if events_received and int(events_received) > 0:
                    log_capi_ok("Meta", order.order_number, event_id, response.status_code, body)
                    return True
                log_capi_fail("Meta", order.order_number, event_id, response.status_code, body)
                return False

            log_capi_fail("Meta", order.order_number, event_id, response.status_code, body)
            return False
    except Exception as exc:
        log_capi_error("Meta", order.order_number, event_id, exc)
        return False
