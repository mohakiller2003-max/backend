import asyncio
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.db.models import Order
from app.db.session import SessionLocal, get_db
from app.schemas.orders import (
    AcceptUpsellRequest,
    AcceptUpsellResponse,
    CreateOrderRequest,
    CreateOrderResponse,
)
from app.services import cod_network as cod_network_service
from app.services import orders as order_service
from app.services import sheets as sheet_service
from app.services.tracking import meta, snap, tiktok
from app.utils.geoip import lookup_country
from app.utils.phone import InvalidPhoneError, normalize_uae_phone

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/orders", tags=["orders"])

TEST_PHONE_E164 = "+971556710680"


def is_ip_allowed(ip: str, phone: str) -> bool:
    if not ip or ip.startswith(("127.", "::1", "localhost")):
        return True

    try:
        if normalize_uae_phone(phone) == TEST_PHONE_E164:
            return True
    except InvalidPhoneError:
        pass

    return lookup_country(ip).is_uae

@router.post("", response_model=CreateOrderResponse, status_code=201)
async def create_order(
    request_body: CreateOrderRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    client_ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else "")
    client_ip = client_ip.split(",")[0].strip() if client_ip else ""
    user_agent = request.headers.get("User-Agent", "")

    if not is_ip_allowed(client_ip, request_body.customer.phone):
        raise HTTPException(status_code=403, detail={"code": "GEO_BLOCKED", "message": "Orders are currently only accepted from the United Arab Emirates."})

    geo = lookup_country(client_ip)

    try:
        result = order_service.create_order(
            db=db,
            request=request_body,
            client_ip=client_ip,
            user_agent=user_agent,
            country_code=geo.country_code,
            is_uae_ip=geo.is_uae,
        )
    except ValueError as exc:
        code = str(exc).split(":")[0]
        raise HTTPException(status_code=422, detail={"code": code, "message": str(exc)})

    order = db.query(Order).filter(Order.id == result.order_id).first()
    if order:
        fbp = getattr(request_body.tracking, "fbp", None) if request_body.tracking else None
        fbc = getattr(request_body.tracking, "fbc", None) if request_body.tracking else None
        logger.info(
            "Scheduling CAPI for order=%s event_id=%s",
            order.order_number,
            order.purchase_event_id or order.id,
        )
        background_tasks.add_task(_post_order_tasks, str(order.id), fbp, fbc)

    return result


async def _post_order_tasks(order_id: str, fbp=None, fbc=None):
    """Fire-and-forget: sheet webhook, COD Network, and CAPI — uses its own DB session."""
    db = SessionLocal()
    try:
        order = (
            db.query(Order)
            .options(joinedload(Order.items))
            .filter(Order.id == order_id)
            .first()
        )
        if not order:
            logger.warning("Post-order tasks: order not found id=%s", order_id)
            return

        cod_ok, lead_id = await cod_network_service.create_lead(order)
        if cod_ok:
            order.status = "sent_to_cod"
            if lead_id:
                order.cod_lead_id = lead_id
        elif settings.COD_NETWORK_API_TOKEN:
            order.status = "failed_cod"

        sheet_ok = await sheet_service.send_order_to_sheet(order)
        if sheet_ok and order.status not in ("sent_to_cod",):
            order.status = "sent_to_sheet"
        elif not sheet_ok and order.status == "new":
            order.status = "failed_sheet"

        try:
            db.commit()
        except Exception:
            logger.exception("Post-order tasks commit failed order=%s", order.order_number)

        results = await asyncio.gather(
            meta.send_purchase_event(order, fbp=fbp, fbc=fbc),
            tiktok.send_purchase_event(order),
            snap.send_purchase_event(order),
            return_exceptions=True,
        )
        labels = ("Meta", "TikTok", "Snap")
        for label, result in zip(labels, results):
            if isinstance(result, Exception):
                logger.error("[CAPI:%s] unhandled error order=%s: %s", label, order.order_number, result)
            else:
                logger.info("[CAPI:%s] purchase result order=%s ok=%s", label, order.order_number, result)
    finally:
        db.close()


@router.post("/{order_id}/upsell", response_model=AcceptUpsellResponse)
async def accept_upsell(
    order_id: str,
    request_body: AcceptUpsellRequest,
    db: Session = Depends(get_db),
):
    try:
        result = order_service.accept_upsell(db=db, order_id=order_id, request=request_body)
    except ValueError as exc:
        code = str(exc).split(":")[0]
        status_code = 404 if code == "ORDER_NOT_FOUND" else 422
        raise HTTPException(status_code=status_code, detail={"code": code, "message": str(exc)})
    return result
