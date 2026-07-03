import json
import logging
from typing import Optional, Tuple

import httpx

from app.core.config import PRODUCT_CATALOG, settings
from app.db.models import Order

logger = logging.getLogger(__name__)

COD_STATUS_MAP = {
    "confirmed": "confirmed",
    "shipped": "shipped",
    "delivered": "delivered",
    "returned": "returned",
    "canceled": "cancelled",
    "cancelled": "cancelled",
}


def _referral_id_for_order(order: Order) -> Optional[str]:
    if not order.items:
        return settings.COD_NETWORK_DEFAULT_REFERRAL_ID or None

    product_id = order.items[0].product_id
    referral_ids = {
        "tranexamic-niacinamide-serum": settings.COD_NETWORK_REFERRAL_TRANEXAMIC,
        "azelaic-acne-marks-serum": settings.COD_NETWORK_REFERRAL_AZELAIC,
    }
    referral_id = referral_ids.get(product_id) or settings.COD_NETWORK_DEFAULT_REFERRAL_ID
    return referral_id or None


def _build_note(order: Order) -> str:
    lines = []
    for item in order.items:
        lines.append(
            f"{item.quantity}x {item.product_name_en} ({item.unit_context}) = {float(item.bundle_price_aed)} AED"
        )
    if float(order.upsell_total_aed) > 0:
        lines.append(f"Upsell total: {float(order.upsell_total_aed)} AED")
    lines.append(f"Order total: {float(order.total_aed)} AED")
    return " | ".join(lines)


def _build_payload(order: Order) -> Optional[dict]:
    referral_id = _referral_id_for_order(order)
    if not referral_id:
        logger.warning("COD Network referral_id missing order=%s", order.order_number)
        return None

    quantity = sum(item.quantity for item in order.items) or 1
    phone = order.phone_raw or order.phone_e164

    return {
        "referral_id": referral_id,
        "name": order.customer_name,
        "phone": phone,
        "address": settings.COD_NETWORK_PENDING_ADDRESS,
        "subid": order.order_number,
        "subid2": str(order.id),
        "city": settings.COD_NETWORK_DEFAULT_CITY,
        "country": settings.COD_NETWORK_DEFAULT_COUNTRY,
        "quantity": quantity,
        "note": _build_note(order),
    }


async def create_lead(order: Order) -> Tuple[bool, Optional[str]]:
    """Push order to COD Network as a lead. Returns (success, lead_id)."""
    if not settings.COD_NETWORK_API_TOKEN:
        logger.warning("COD_NETWORK_API_TOKEN not configured, skipping COD Network lead.")
        return False, None

    payload = _build_payload(order)
    if not payload:
        return False, None

    url = f"{settings.COD_NETWORK_API_URL.rstrip('/')}/affiliate/leads"
    headers = {
        "Authorization": f"Bearer {settings.COD_NETWORK_API_TOKEN}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=settings.ORDER_WEBHOOK_TIMEOUT_SECONDS) as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code == 201:
                body = response.json()
                lead_id = str(body.get("data", {}).get("id", "")) or None
                logger.info("COD Network lead created order=%s lead_id=%s", order.order_number, lead_id)
                return True, lead_id

            logger.warning(
                "COD Network lead failed order=%s status=%s body=%s",
                order.order_number,
                response.status_code,
                response.text[:300],
            )
            return False, None
    except Exception as exc:
        logger.error("COD Network lead error order=%s error=%s", order.order_number, str(exc))
        return False, None


def map_cod_status(status: str) -> Optional[str]:
    return COD_STATUS_MAP.get((status or "").strip().lower())
