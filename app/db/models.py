import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Integer, Numeric, Text, DateTime, ForeignKey, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.session import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_number = Column(String(32), unique=True, nullable=False, index=True)
    locale = Column(String(8), nullable=False, default="ar")

    customer_name = Column(String(256), nullable=False)
    phone_raw = Column(String(64), nullable=False)
    phone_e164 = Column(String(20), nullable=False)

    status = Column(
        String(32),
        nullable=False,
        default="new",
    )

    subtotal_aed = Column(Numeric(10, 2), nullable=False)
    upsell_total_aed = Column(Numeric(10, 2), nullable=False, default=0)
    total_aed = Column(Numeric(10, 2), nullable=False)

    currency = Column(String(8), nullable=False, default="AED")
    payment_method = Column(String(32), nullable=False, default="COD")

    utm_source = Column(String(256))
    utm_medium = Column(String(256))
    utm_campaign = Column(String(256))
    utm_content = Column(String(256))
    utm_term = Column(String(256))
    fbclid = Column(String(512))
    ttclid = Column(String(512))
    sc_click_id = Column(String(512))

    client_ip = Column(String(64))
    user_agent = Column(Text)
    landing_page = Column(Text)
    referrer = Column(Text)

    purchase_event_id = Column(String(256))
    cod_lead_id = Column(String(64), nullable=True, index=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    tracking_events = relationship("TrackingEvent", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = Column(String(36), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)

    product_id = Column(String(128), nullable=False)
    product_name_ar = Column(String(512), nullable=False)
    product_name_en = Column(String(512), nullable=False)
    quantity = Column(Integer, nullable=False)
    bundle_price_aed = Column(Numeric(10, 2), nullable=False)
    unit_context = Column(
        String(32),
        nullable=False,
        default="bundle",
    )

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    order = relationship("Order", back_populates="items")


class TrackingEvent(Base):
    __tablename__ = "tracking_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = Column(String(36), ForeignKey("orders.id", ondelete="CASCADE"), nullable=True)

    event_name = Column(String(128), nullable=False)
    event_id = Column(String(256))
    platform = Column(String(64), nullable=False)
    payload_json = Column(Text)
    response_json = Column(Text)
    status = Column(String(32), nullable=False, default="pending")

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    order = relationship("Order", back_populates="tracking_events")
