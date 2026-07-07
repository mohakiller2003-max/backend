import logging
import time

import httpx

from app.core.config import settings
from app.db.models import Order
from app.services.tracking.capi_log import log_capi_error, log_capi_fail, log_capi_ok, log_capi_send, log_capi_skip
from app.utils.phone import snap_hash_phone

logger = logging.getLogger(__name__)


def _snap_capi_url() -> str:
    return f"https://tr.snapchat.com/v3/{settings.SNAP_PIXEL_ID}/events"


async def send_purchase_event(order: Order) -> bool:
    """Send PURCHASE to Snapchat Conversions API v3 (hashed phone on server)."""
    if not settings.SNAP_PIXEL_ID or not settings.SNAP_ACCESS_TOKEN:
        log_capi_skip("Snap", "SNAP_PIXEL_ID or SNAP_ACCESS_TOKEN not set")
        return False

    event_id = order.purchase_event_id or str(order.id)
    log_capi_send("Snap", order.order_number, event_id)

    phone_hash = snap_hash_phone(order.phone_e164)

    bundle_items = [item for item in order.items if item.unit_context == "bundle"]
    contents = [
        {
            "id": item.product_id,
            "quantity": str(item.quantity),
            "item_price": str(float(item.bundle_price_aed)),
        }
        for item in bundle_items
    ]

    user_data: dict = {
        "ph": [phone_hash],
        "client_ip_address": order.client_ip or "",
        "client_user_agent": order.user_agent or "",
    }
    if order.sc_click_id:
        user_data["sc_click_id"] = order.sc_click_id

    event = {
        "event_name": "PURCHASE",
        "event_time": int(time.time()),
        "event_id": event_id,
        "action_source": "WEB",
        "event_source_url": order.landing_page or settings.FRONTEND_BASE_URL,
        "user_data": user_data,
        "custom_data": {
            "currency": "AED",
            "value": str(float(order.total_aed)),
            "order_id": order.order_number,
            "content_ids": [item.product_id for item in bundle_items],
            "contents": contents,
            "num_items": sum(item.quantity for item in bundle_items),
        },
    }

    payload = {"data": [event]}
    params = {"access_token": settings.SNAP_ACCESS_TOKEN}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(_snap_capi_url(), params=params, json=payload)
            try:
                body = response.json() if response.content else {}
            except ValueError:
                body = {"raw": response.text[:500]}

            if response.status_code in (200, 204):
                status = str(body.get("status", "VALID")).upper() if isinstance(body, dict) else "VALID"
                if status in ("VALID", "SUCCESS", "OK", ""):
                    log_capi_ok("Snap", order.order_number, event_id, response.status_code, body)
                    return True
                log_capi_fail("Snap", order.order_number, event_id, response.status_code, body)
                return False

            log_capi_fail("Snap", order.order_number, event_id, response.status_code, body)
            return False
    except Exception as exc:
        log_capi_error("Snap", order.order_number, event_id, exc)
        return False
