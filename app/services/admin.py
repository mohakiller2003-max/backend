from datetime import date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import func, distinct
from sqlalchemy.orm import Session, joinedload

from app.db.models import AnalyticsEvent, Order, OrderItem, TrackingEvent


def _day_bounds(date_from: date, date_to: date) -> tuple[datetime, datetime]:
    start = datetime.combine(date_from, time.min)
    end = datetime.combine(date_to + timedelta(days=1), time.min)
    return start, end


def get_metrics(db: Session, date_from: date, date_to: date, uae_only: bool = True) -> dict:
    start, end = _day_bounds(date_from, date_to)

    event_filters = [
        AnalyticsEvent.created_at >= start,
        AnalyticsEvent.created_at < end,
    ]
    order_filters = [
        Order.created_at >= start,
        Order.created_at < end,
    ]
    if uae_only:
        event_filters.append(AnalyticsEvent.is_uae_ip.is_(True))
        order_filters.append(Order.is_uae_ip.is_(True))

    def count_events(event_type: str) -> int:
        return (
            db.query(func.count(AnalyticsEvent.id))
            .filter(*event_filters, AnalyticsEvent.event_type == event_type)
            .scalar()
            or 0
        )

    unique_sessions = (
        db.query(func.count(distinct(AnalyticsEvent.session_id)))
        .filter(*event_filters)
        .scalar()
        or 0
    )

    orders_q = db.query(Order).filter(*order_filters)
    orders_count = orders_q.count()
    revenue = (
        db.query(func.coalesce(func.sum(Order.total_aed), 0))
        .filter(*order_filters)
        .scalar()
        or Decimal("0")
    )
    upsell_orders = (
        db.query(func.count(Order.id))
        .filter(*order_filters, Order.upsell_total_aed > 0)
        .scalar()
        or 0
    )

    status_rows = (
        db.query(Order.status, func.count(Order.id))
        .filter(*order_filters)
        .group_by(Order.status)
        .all()
    )

    utm_rows = (
        db.query(Order.utm_source, func.count(Order.id))
        .filter(*order_filters, Order.utm_source.isnot(None), Order.utm_source != "")
        .group_by(Order.utm_source)
        .order_by(func.count(Order.id).desc())
        .limit(5)
        .all()
    )

    conversion = (orders_count / unique_sessions * 100) if unique_sessions else 0.0
    aov = float(revenue / orders_count) if orders_count else 0.0

    return {
        "date_from": date_from,
        "date_to": date_to,
        "uae_only": uae_only,
        "page_views": count_events("page_view"),
        "product_views": count_events("product_view"),
        "add_to_cart": count_events("add_to_cart"),
        "initiate_checkout": count_events("initiate_checkout"),
        "unique_sessions": unique_sessions,
        "orders": orders_count,
        "revenue_aed": float(revenue),
        "upsell_orders": upsell_orders,
        "conversion_rate": round(conversion, 2),
        "aov_aed": round(aov, 2),
        "orders_by_status": {status: count for status, count in status_rows},
        "top_utm_sources": [{"source": src or "direct", "orders": count} for src, count in utm_rows],
    }


def list_orders(
    db: Session,
    page: int,
    page_size: int,
    date_from: date | None,
    date_to: date | None,
    status: str | None,
    uae_only: bool,
    search: str | None,
) -> tuple[int, list[Order]]:
    q = db.query(Order)
    if uae_only:
        q = q.filter(Order.is_uae_ip.is_(True))
    if date_from:
        q = q.filter(Order.created_at >= datetime.combine(date_from, time.min))
    if date_to:
        q = q.filter(Order.created_at < datetime.combine(date_to + timedelta(days=1), time.min))
    if status:
        q = q.filter(Order.status == status)
    if search:
        like = f"%{search.strip()}%"
        q = q.filter(
            (Order.order_number.ilike(like))
            | (Order.customer_name.ilike(like))
            | (Order.phone_e164.ilike(like))
            | (Order.phone_raw.ilike(like))
        )
    total = q.count()
    items = (
        q.order_by(Order.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return total, items


def get_order_detail(db: Session, order_id: str) -> Order | None:
    return (
        db.query(Order)
        .options(joinedload(Order.items), joinedload(Order.tracking_events))
        .filter(Order.id == order_id)
        .first()
    )
