import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Order, TrackingEvent
from app.db.session import get_db
from app.services import cod_network

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class CodNetworkLeadWebhook(BaseModel):
    lead_id: str
    status: str
    subid: str | None = None
    subid2: str | None = None


def _verify_webhook_secret(request: Request) -> None:
    if not settings.COD_NETWORK_WEBHOOK_SECRET:
        return

    provided = (
        request.headers.get("X-Webhook-Secret")
        or request.headers.get("X-COD-Network-Secret")
        or request.query_params.get("secret")
    )
    if provided != settings.COD_NETWORK_WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail={"code": "INVALID_WEBHOOK_SECRET"})


@router.post("/cod-network")
async def cod_network_webhook(
    payload: CodNetworkLeadWebhook,
    request: Request,
    db: Session = Depends(get_db),
):
    _verify_webhook_secret(request)

    order = None
    if payload.subid:
        order = db.query(Order).filter(Order.order_number == payload.subid).first()
    if not order and payload.subid2:
        order = db.query(Order).filter(Order.id == payload.subid2).first()
    if not order and payload.lead_id:
        order = db.query(Order).filter(Order.cod_lead_id == payload.lead_id).first()

    if not order:
        logger.warning(
            "COD Network webhook order not found lead_id=%s subid=%s subid2=%s",
            payload.lead_id,
            payload.subid,
            payload.subid2,
        )
        raise HTTPException(status_code=404, detail={"code": "ORDER_NOT_FOUND"})

    mapped_status = cod_network.map_cod_status(payload.status)
    if mapped_status:
        order.status = mapped_status
    if payload.lead_id:
        order.cod_lead_id = payload.lead_id

    event = TrackingEvent(
        order_id=order.id,
        event_name=f"cod_network_{payload.status}",
        event_id=payload.lead_id,
        platform="cod_network",
        payload_json=json.dumps(payload.model_dump()),
        status="received",
    )
    db.add(event)
    db.commit()

    logger.info(
        "COD Network webhook processed order=%s lead_id=%s status=%s",
        order.order_number,
        payload.lead_id,
        payload.status,
    )
    return {"ok": True, "order_number": order.order_number, "status": order.status}
