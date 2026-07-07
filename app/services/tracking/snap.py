import logging
import time

import httpx

from app.core.config import settings
from app.db.models import Order
from app.utils.phone import snap_hash_phone

logger = logging.getLogger(__name__)


def _snap_capi_url() -> str:
    return f"https://tr.snapchat.com/v3/{settings.SNAP_PIXEL_ID}/events"


async def send_purchase_event(order: Order) -> bool:
    """Send PURCHASE server-side event to Snapchat Conversions API v3."""
    if not settings.SNAP_PIXEL_ID or not settings.SNAP_ACCESS_TOKEN:
        logger.info("Snapchat CAPI not configured, skipping.")
        return False

    phone_hash = snap_hash_phone(order.phone_e164)
    event_id = order.purchase_event_id or str(order.id)

    contents = [
        {
            "id": item.product_id,
            "quantity": str(item.quantity),
            "item_price": str(float(item.bundle_price_aed)),
        }
        for item in order.items
        if item.unit_context == "bundle"
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
            "content_ids": [item.product_id for item in order.items if item.unit_context == "bundle"],
            "contents": contents,
            "num_items": sum(item.quantity for item in order.items if item.unit_context == "bundle"),
        },
    }

    payload = {"data": [event]}
    params = {"access_token": settings.SNAP_ACCESS_TOKEN}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                _snap_capi_url(),
                params=params,
                json=payload,
            )
            if response.status_code in (200, 204):
                body: dict = {}
                if response.content:
                    try:
                        body = response.json()
                    except ValueError:
                        body = {}
                status = str(body.get("status", "VALID")).upper()
                if status in ("VALID", "SUCCESS", "OK", ""):
                    logger.info("Snap CAPI purchase sent order=%s", order.order_number)
                    return True
                logger.warning(
                    "Snap CAPI rejected order=%s status=%s body=%s",
                    order.order_number,
                    status,
                    response.text[:300],
                )
                return False
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
