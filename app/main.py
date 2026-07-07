import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes import admin, analytics, health, orders, webhooks

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

logger = logging.getLogger(__name__)

_capi_platforms = []
if settings.META_PIXEL_ID and settings.META_ACCESS_TOKEN:
    _capi_platforms.append(f"Meta({settings.META_PIXEL_ID[:6]}…)")
if settings.TIKTOK_PIXEL_ID and settings.TIKTOK_ACCESS_TOKEN:
    _capi_platforms.append(f"TikTok({settings.TIKTOK_PIXEL_ID[:6]}…)")
if settings.SNAP_PIXEL_ID and settings.SNAP_ACCESS_TOKEN:
    _capi_platforms.append(f"Snap({settings.SNAP_PIXEL_ID[:6]}…)")

if _capi_platforms:
    logger.info("[CAPI] configured platforms: %s", ", ".join(_capi_platforms))
else:
    logger.warning("[CAPI] no platforms configured — set PIXEL_ID + ACCESS_TOKEN env vars")

app = FastAPI(
    title="Skinouva API",
    version="1.0.0",
    docs_url="/docs" if settings.APP_ENV != "production" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(health.router)
app.include_router(analytics.router)
app.include_router(orders.router)
app.include_router(webhooks.router)
app.include_router(admin.router)
