import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import PRODUCT_CATALOG, UPSELL_PRICE_AED, settings
from app.db.models import Order, OrderItem
from app.schemas.orders import (
    AcceptUpsellRequest,
    AcceptUpsellResponse,
    CreateOrderRequest,
    CreateOrderResponse,
    UpsellProduct,
)
from app.utils.phone import InvalidPhoneError, normalize_uae_phone

logger = logging.getLogger(__name__)

ORDER_COUNTER_START = 10001


ORDER_NUMBER_PREFIX = "SKINOVA"


def _next_order_number(db: Session) -> str:
    count = db.query(Order).count()
    return f"{ORDER_NUMBER_PREFIX}-{ORDER_COUNTER_START + count}"


def _recalculate_total(items: list) -> Decimal:
    """Recalculate order total from server-side pricing. Never trust frontend totals."""
    total = Decimal("0")
    for item in items:
        product = PRODUCT_CATALOG.get(item.product_id)
        if not product:
            raise ValueError(f"INVALID_PRODUCT:{item.product_id}")
        server_price = product["offers"].get(item.quantity)
        if server_price is None:
            raise ValueError(f"INVALID_OFFER:{item.product_id}:{item.quantity}")
        total += Decimal(str(server_price))
    return total


def create_order(
    db: Session,
    request: CreateOrderRequest,
    client_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    country_code: Optional[str] = None,
    is_uae_ip: bool = False,
) -> CreateOrderResponse:
    try:
        phone_e164 = normalize_uae_phone(request.customer.phone)
    except InvalidPhoneError as exc:
        raise ValueError(f"INVALID_PHONE:{exc}") from exc

    subtotal = _recalculate_total(request.items)
    total = subtotal

    order_number = _next_order_number(db)
    tracking = request.tracking

    order = Order(
        order_number=order_number,
        locale=request.locale,
        customer_name=request.customer.name.strip(),
        phone_raw=request.customer.phone.strip(),
        phone_e164=phone_e164,
        status="new",
        subtotal_aed=subtotal,
        upsell_total_aed=Decimal("0"),
        total_aed=total,
        currency="AED",
        payment_method="COD",
        client_ip=client_ip,
        country_code=country_code,
        is_uae_ip=is_uae_ip,
        user_agent=user_agent,
        purchase_event_id=tracking.purchase_event_id if tracking else None,
        utm_source=tracking.utm_source if tracking else None,
        utm_medium=tracking.utm_medium if tracking else None,
        utm_campaign=tracking.utm_campaign if tracking else None,
        utm_content=tracking.utm_content if tracking else None,
        utm_term=tracking.utm_term if tracking else None,
        fbclid=tracking.fbclid if tracking else None,
        ttclid=tracking.ttclid if tracking else None,
        sc_click_id=tracking.sc_click_id if tracking else None,
        landing_page=tracking.landing_page if tracking else None,
        referrer=tracking.referrer if tracking else None,
    )
    db.add(order)
    db.flush()

    for item in request.items:
        product = PRODUCT_CATALOG[item.product_id]
        server_price = product["offers"][item.quantity]
        db.add(OrderItem(
            order_id=order.id,
            product_id=item.product_id,
            product_name_ar=product["name_ar"],
            product_name_en=product["name_en"],
            quantity=item.quantity,
            bundle_price_aed=Decimal(str(server_price)),
            unit_context="bundle",
        ))

    db.commit()
    db.refresh(order)

    # Determine upsell offer: complementary product at 99 AED.
    main_product_ids = [i.product_id for i in request.items]
    upsell_product = None
    if len(main_product_ids) == 1:
        comp_id = PRODUCT_CATALOG[main_product_ids[0]].get("complementary")
        if comp_id:
            upsell_product = UpsellProduct(product_id=comp_id, price_aed=UPSELL_PRICE_AED)
    elif len(main_product_ids) > 1:
        first_comp = PRODUCT_CATALOG.get(main_product_ids[0], {}).get("complementary")
        if first_comp and first_comp not in main_product_ids:
            upsell_product = UpsellProduct(product_id=first_comp, price_aed=UPSELL_PRICE_AED)

    return CreateOrderResponse(
        order_id=order.id,
        order_number=order.order_number,
        total_aed=float(order.total_aed),
        upsell=upsell_product,
    )


def accept_upsell(
    db: Session,
    order_id: str,
    request: AcceptUpsellRequest,
) -> AcceptUpsellResponse:
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise ValueError("ORDER_NOT_FOUND")

    if order.status == "upsell_added" or float(order.upsell_total_aed) > 0:
        raise ValueError("UPSELL_ALREADY_ADDED")

    if request.price_aed != UPSELL_PRICE_AED:
        raise ValueError(f"INVALID_OFFER:upsell price must be {UPSELL_PRICE_AED}")

    product = PRODUCT_CATALOG.get(request.product_id)
    if not product:
        raise ValueError(f"INVALID_PRODUCT:{request.product_id}")

    main_ids = [item.product_id for item in order.items if item.unit_context == "bundle"]
    expected_comp = None
    if main_ids:
        expected_comp = PRODUCT_CATALOG.get(main_ids[0], {}).get("complementary")

    if expected_comp and request.product_id != expected_comp:
        raise ValueError(f"INVALID_PRODUCT:not complementary")

    upsell_price = Decimal(str(UPSELL_PRICE_AED))

    db.add(OrderItem(
        order_id=order.id,
        product_id=request.product_id,
        product_name_ar=product["name_ar"],
        product_name_en=product["name_en"],
        quantity=1,
        bundle_price_aed=upsell_price,
        unit_context="upsell",
    ))

    order.upsell_total_aed = upsell_price
    order.total_aed = order.total_aed + upsell_price
    order.status = "upsell_added"
    order.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(order)

    return AcceptUpsellResponse(
        order_id=order.id,
        order_number=order.order_number,
        total_aed=float(order.total_aed),
        upsell_accepted=True,
    )
