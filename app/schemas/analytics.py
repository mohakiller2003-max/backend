from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AnalyticsEventIn(BaseModel):
    event_type: str = Field(..., min_length=1, max_length=64)
    session_id: str = Field(..., min_length=8, max_length=64)
    page_path: Optional[str] = None
    product_id: Optional[str] = None
    locale: Optional[str] = Field(default="ar", pattern="^(ar|en)$")
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    referrer: Optional[str] = None


class AnalyticsEventResponse(BaseModel):
    ok: bool = True
