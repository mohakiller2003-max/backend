from sqlalchemy.orm import Session

from app.db.models import AnalyticsEvent
from app.schemas.analytics import AnalyticsEventIn
from app.utils.geoip import lookup_country


def record_event(
    db: Session,
    payload: AnalyticsEventIn,
    client_ip: str | None,
    user_agent: str | None,
) -> AnalyticsEvent:
    geo = lookup_country(client_ip)
    event = AnalyticsEvent(
        event_type=payload.event_type,
        session_id=payload.session_id,
        page_path=payload.page_path,
        product_id=payload.product_id,
        locale=payload.locale,
        client_ip=client_ip,
        country_code=geo.country_code,
        is_uae_ip=geo.is_uae,
        utm_source=payload.utm_source,
        utm_medium=payload.utm_medium,
        utm_campaign=payload.utm_campaign,
        referrer=payload.referrer,
        user_agent=user_agent,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
