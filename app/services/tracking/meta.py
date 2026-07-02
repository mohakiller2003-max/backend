import json
import logging
import time
from typing import Optional

import httpx

from app.core.config import settings
from app.db.models import Order
from app.utils.phone import meta_hash_phone

logger = logging.getLogger(__name__)

META_CAPI_URL = "https://graph.facebook.com/v19.0/{pixel_id}/events"


async def send_purchase_event(
    order: Order,
    fbp: Optional[str] = None,
    fbc: Optional[str] = None,
) -> bool:
    """Send Purchase server-side event to Meta Conversions API."""
    if not settings.META_PIXEL_ID or not settings.META_ACCESS_TOKEN:
        logger.info("Meta CAPI not configured, skipping.")
        return False

    phone_hash = meta_hash_phone(order.phone_e164)

    user_data: dict = {
        "ph": [phone_hash],
        "client_ip_address": order.client_ip or "",
        "client_user_agent": order.user_agent or "",
    }
    if fbp:
        user_data["fbp"] = fbp
    if fbc or order.fbclid:
        user_data["fbc"] = fbc or f"fb.1.{int(time.time() * 1000)}.{order.fbclid}"

    contents = [
        {"id": item.product_id, "quantity": item.quantity}
        for item in order.items
        if item.unit_context == "bundle"
    ]
    content_ids = [item.product_id for item in order.items if item.unit_context == "bundle"]

    event = {
        "event_name": "Purchase",
        "event_time": int(time.time()),
        "event_id": order.purchase_event_id or str(order.id),
        "action_source": "website",
        "event_source_url": order.landing_page or settings.FRONTEND_BASE_URL,
        "user_data": user_data,
        "custom_data": {
            "currency": "AED",
            "value": float(order.total_aed),
            "contents": contents,
            "content_ids": content_ids,
            "content_type": "product",
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
            if response.status_code == 200:
                logger.info("Meta CAPI purchase sent order=%s", order.order_number)
                return True
            logger.warning(
                "Meta CAPI non-200 order=%s status=%s body=%s",
                order.order_number,
                response.status_code,
                response.text[:300],
            )
            return False
    except Exception as exc:
        logger.error("Meta CAPI error order=%s error=%s", order.order_number, str(exc))
        return False
