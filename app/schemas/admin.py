from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class AdminLoginResponse(BaseModel):
    token: str
    expires_in: int


class AdminMetricsResponse(BaseModel):
    date_from: date
    date_to: date
    uae_only: bool = True
    page_views: int
    product_views: int
    add_to_cart: int
    initiate_checkout: int
    unique_sessions: int
    orders: int
    revenue_aed: float
    upsell_orders: int
    conversion_rate: float
    aov_aed: float
    orders_by_status: dict[str, int]
    top_utm_sources: list[dict[str, str | int]]


class AdminOrderItemOut(BaseModel):
    product_id: str
    product_name_ar: str
    product_name_en: str
    quantity: int
    bundle_price_aed: float
    unit_context: str


class AdminOrderListItem(BaseModel):
    id: str
    order_number: str
    customer_name: str
    phone_e164: str
    status: str
    total_aed: float
    locale: str
    country_code: Optional[str]
    is_uae_ip: bool
    utm_source: Optional[str]
    utm_campaign: Optional[str]
    created_at: datetime


class AdminOrderListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[AdminOrderListItem]


class AdminTrackingEventOut(BaseModel):
    event_name: str
    platform: str
    status: str
    created_at: datetime


class AdminOrderDetail(AdminOrderListItem):
    phone_raw: str
    subtotal_aed: float
    upsell_total_aed: float
    payment_method: str
    utm_medium: Optional[str]
    utm_content: Optional[str]
    utm_term: Optional[str]
    fbclid: Optional[str]
    ttclid: Optional[str]
    sc_click_id: Optional[str]
    client_ip: Optional[str]
    user_agent: Optional[str]
    landing_page: Optional[str]
    referrer: Optional[str]
    cod_lead_id: Optional[str]
    updated_at: datetime
    items: list[AdminOrderItemOut]
    tracking_events: list[AdminTrackingEventOut]


class AdminOrderStatusUpdate(BaseModel):
    status: str = Field(..., min_length=2, max_length=32)
