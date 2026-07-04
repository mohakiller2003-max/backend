from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps.admin import require_admin
from app.core.config import settings
from app.db.session import get_db
from app.schemas.admin import (
    AdminLoginRequest,
    AdminLoginResponse,
    AdminMetricsResponse,
    AdminOrderDetail,
    AdminOrderItemOut,
    AdminOrderListItem,
    AdminOrderListResponse,
    AdminOrderStatusUpdate,
    AdminTrackingEventOut,
)
from app.services import admin as admin_service
from app.services.admin_auth import admin_enabled, create_admin_token, verify_credentials

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/auth/login", response_model=AdminLoginResponse)
def admin_login(payload: AdminLoginRequest):
    if not admin_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "ADMIN_DISABLED", "message": "Admin credentials not configured"},
        )
    if not verify_credentials(payload.username, payload.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_CREDENTIALS", "message": "Invalid username or password"},
        )
    return AdminLoginResponse(
        token=create_admin_token(),
        expires_in=settings.ADMIN_SESSION_TTL_SECONDS,
    )


@router.get("/metrics", response_model=AdminMetricsResponse, dependencies=[Depends(require_admin)])
def admin_metrics(
    date_from: date = Query(...),
    date_to: date = Query(...),
    uae_only: bool = Query(default=True),
    db: Session = Depends(get_db),
):
    if date_to < date_from:
        raise HTTPException(status_code=400, detail="date_to must be >= date_from")
    return admin_service.get_metrics(db, date_from, date_to, uae_only)


@router.get("/orders", response_model=AdminOrderListResponse, dependencies=[Depends(require_admin)])
def admin_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    date_from: date | None = None,
    date_to: date | None = None,
    status: str | None = None,
    uae_only: bool = Query(default=True),
    search: str | None = None,
    db: Session = Depends(get_db),
):
    total, orders = admin_service.list_orders(
        db, page, page_size, date_from, date_to, status, uae_only, search
    )
    return AdminOrderListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[
            AdminOrderListItem(
                id=o.id,
                order_number=o.order_number,
                customer_name=o.customer_name,
                phone_e164=o.phone_e164,
                status=o.status,
                total_aed=float(o.total_aed),
                locale=o.locale,
                country_code=o.country_code,
                is_uae_ip=bool(o.is_uae_ip),
                utm_source=o.utm_source,
                utm_campaign=o.utm_campaign,
                created_at=o.created_at,
            )
            for o in orders
        ],
    )


def _order_detail(o) -> AdminOrderDetail:
    return AdminOrderDetail(
        id=o.id,
        order_number=o.order_number,
        customer_name=o.customer_name,
        phone_e164=o.phone_e164,
        phone_raw=o.phone_raw,
        status=o.status,
        subtotal_aed=float(o.subtotal_aed),
        upsell_total_aed=float(o.upsell_total_aed),
        total_aed=float(o.total_aed),
        payment_method=o.payment_method,
        locale=o.locale,
        country_code=o.country_code,
        is_uae_ip=bool(o.is_uae_ip),
        utm_source=o.utm_source,
        utm_medium=o.utm_medium,
        utm_campaign=o.utm_campaign,
        utm_content=o.utm_content,
        utm_term=o.utm_term,
        fbclid=o.fbclid,
        ttclid=o.ttclid,
        sc_click_id=o.sc_click_id,
        client_ip=o.client_ip,
        user_agent=o.user_agent,
        landing_page=o.landing_page,
        referrer=o.referrer,
        cod_lead_id=o.cod_lead_id,
        created_at=o.created_at,
        updated_at=o.updated_at,
        items=[
            AdminOrderItemOut(
                product_id=i.product_id,
                product_name_ar=i.product_name_ar,
                product_name_en=i.product_name_en,
                quantity=i.quantity,
                bundle_price_aed=float(i.bundle_price_aed),
                unit_context=i.unit_context,
            )
            for i in o.items
        ],
        tracking_events=[
            AdminTrackingEventOut(
                event_name=e.event_name,
                platform=e.platform,
                status=e.status,
                created_at=e.created_at,
            )
            for e in o.tracking_events
        ],
    )


@router.get("/orders/{order_id}", response_model=AdminOrderDetail, dependencies=[Depends(require_admin)])
def admin_order_detail(order_id: str, db: Session = Depends(get_db)):
    order = admin_service.get_order_detail(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return _order_detail(order)


@router.patch("/orders/{order_id}/status", response_model=AdminOrderDetail, dependencies=[Depends(require_admin)])
def admin_update_order_status(
    order_id: str,
    payload: AdminOrderStatusUpdate,
    db: Session = Depends(get_db),
):
    order = admin_service.get_order_detail(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    order.status = payload.status.strip()
    db.commit()
    db.refresh(order)
    return _order_detail(order)
