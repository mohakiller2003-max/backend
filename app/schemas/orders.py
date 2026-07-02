from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID


class CustomerIn(BaseModel):
    name: str = Field(..., min_length=2, max_length=256)
    phone: str = Field(..., min_length=9, max_length=20)


class OrderItemIn(BaseModel):
    product_id: str
    quantity: int = Field(..., ge=1, le=3)
    price_aed: float


class TrackingIn(BaseModel):
    purchase_event_id: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    utm_content: Optional[str] = None
    utm_term: Optional[str] = None
    fbclid: Optional[str] = None
    ttclid: Optional[str] = None
    sc_click_id: Optional[str] = None
    landing_page: Optional[str] = None
    referrer: Optional[str] = None
    fbp: Optional[str] = None
    fbc: Optional[str] = None


class TotalsIn(BaseModel):
    subtotal_aed: float
    total_aed: float


class CreateOrderRequest(BaseModel):
    locale: str = Field(default="ar", pattern="^(ar|en)$")
    customer: CustomerIn
    items: List[OrderItemIn] = Field(..., min_length=1)
    totals: TotalsIn
    tracking: Optional[TrackingIn] = None


class UpsellProduct(BaseModel):
    product_id: str
    price_aed: float


class CreateOrderResponse(BaseModel):
    order_id: UUID
    order_number: str
    total_aed: float
    upsell: Optional[UpsellProduct] = None


class AcceptUpsellRequest(BaseModel):
    product_id: str
    price_aed: float
    event_id: Optional[str] = None


class AcceptUpsellResponse(BaseModel):
    order_id: UUID
    order_number: str
    total_aed: float
    upsell_accepted: bool


class HealthResponse(BaseModel):
    status: str
    database: str
