from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.analytics import AnalyticsEventIn, AnalyticsEventResponse
from app.services import analytics as analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else ""


@router.post("/events", response_model=AnalyticsEventResponse, status_code=201)
def track_event(
    payload: AnalyticsEventIn,
    request: Request,
    db: Session = Depends(get_db),
):
    analytics_service.record_event(
        db=db,
        payload=payload,
        client_ip=_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )
    return AnalyticsEventResponse(ok=True)
