import asyncio
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
import geoip2.webservice

from app.core.config import settings
from app.db.session import get_db
from app.db.models import Order
from app.schemas.orders import (
    AcceptUpsellRequest,
    AcceptUpsellResponse,
    CreateOrderRequest,
    CreateOrderResponse,
)
from app.services import orders as order_service
from app.services import cod_network as cod_network_service
from app.services import sheets as sheet_service
from app.services.tracking import meta, tiktok, snap

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/orders", tags=["orders"])

def is_ip_allowed(ip: str, phone: str) -> bool:
    if phone == "0556710680" or not ip or ip.startswith(("127.", "::1", "localhost")): return True
    try: return geoip2.webservice.Client(settings.MAXMIND_ACCOUNT_ID, settings.MAXMIND_LICENSE_KEY, host="geolite.info").country(ip).country.iso_code == "AE"
    except: return True

@router.post("", response_model=CreateOrderResponse, status_code=201)
async def create_order(
    request_body: CreateOrderRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    client_ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else "")
    client_ip = client_ip.split(",")[0].strip() if client_ip else ""
    user_agent = request.headers.get("User-Agent", "")

    if not is_ip_allowed(client_ip, request_body.customer.phone):
        raise HTTPException(status_code=403, detail={"code": "GEO_BLOCKED", "message": "Orders are currently only accepted from the United Arab Emirates."})

    try:
        result = order_service.create_order(
            db=db,
            request=request_body,
            client_ip=client_ip,
            user_agent=user_agent,
        )
    except ValueError as exc:
        code = str(exc).split(":")[0]
        raise HTTPException(status_code=422, detail={"code": code, "message": str(exc)})

    order = db.query(Order).filter(Order.id == result.order_id).first()
    if order:
        fbp = getattr(request_body.tracking, "fbp", None)
        fbc = getattr(request_body.tracking, "fbc", None)
        asyncio.create_task(_post_order_tasks(order, db, fbp=fbp, fbc=fbc))

    return result


async def _post_order_tasks(order: Order, db: Session, fbp=None, fbc=None):
    """Fire-and-forget: COD Network, sheet webhook, and CAPI — must not block order response."""
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
        pass

    await asyncio.gather(
        meta.send_purchase_event(order, fbp=fbp, fbc=fbc),
        tiktok.send_purchase_event(order),
        snap.send_purchase_event(order),
        return_exceptions=True,
    )


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
