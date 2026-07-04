from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_ENV: str = "production"
    API_BASE_URL: str = "https://api.skinouva.shop"
    FRONTEND_BASE_URL: str = "https://skinouva.shop"
    DATABASE_URL: str = ""
    CORS_ORIGINS: str = "https://skinouva.shop,https://www.skinouva.shop"

    SHEETS_WEBHOOK_URL: str = ""
    SHEETS_WEBHOOK_SECRET: str = ""

    META_PIXEL_ID: str = ""
    META_ACCESS_TOKEN: str = ""
    META_TEST_EVENT_CODE: str = ""

    TIKTOK_PIXEL_ID: str = ""
    TIKTOK_ACCESS_TOKEN: str = ""
    TIKTOK_TEST_EVENT_CODE: str = ""

    SNAP_PIXEL_ID: str = ""
    SNAP_ACCESS_TOKEN: str = ""

    MAXMIND_ACCOUNT_ID: str = ""
    MAXMIND_LICENSE_KEY: str = ""

    COD_NETWORK_API_URL: str = "https://api.cod.network/api/v2"
    COD_NETWORK_API_TOKEN: str = ""
    COD_NETWORK_WEBHOOK_SECRET: str = ""
    COD_NETWORK_DEFAULT_REFERRAL_ID: str = ""
    COD_NETWORK_REFERRAL_TRANEXAMIC: str = ""
    COD_NETWORK_REFERRAL_AZELAIC: str = ""
    COD_NETWORK_DEFAULT_COUNTRY: str = "AE"
    COD_NETWORK_DEFAULT_CITY: str = ""
    COD_NETWORK_PENDING_ADDRESS: str = "UAE - address to be confirmed by phone"

    ORDER_WEBHOOK_TIMEOUT_SECONDS: int = 8
    LOG_LEVEL: str = "info"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        from app.db.url import normalize_database_url as normalize

        return normalize(value) if isinstance(value, str) else value

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()


# Server-side product and pricing constants — backend is the source of truth.
PRODUCT_CATALOG = {
    "tranexamic-niacinamide-serum": {
        "id": "tranexamic-niacinamide-serum",
        "sku": "SKNV-TNM-8842",
        "name_ar": "سيروم الترانيكساميك + النياسيناميد ضد البقع الداكنة وتفاوت لون البشرة",
        "name_en": "Tranexamic + Niacinamide Dark Spot Serum",
        "offers": {1: 199, 2: 279, 3: 349},
        "upsell_price": 99,
        "complementary": "azelaic-acne-marks-serum",
    },
    "azelaic-acne-marks-serum": {
        "id": "azelaic-acne-marks-serum",
        "sku": "SKNV-AZL-3391",
        "name_ar": "سيروم الأزيليك لحب الشباب الهرموني وآثاره",
        "name_en": "Azelaic Serum for Hormonal Acne and Marks",
        "offers": {1: 199, 2: 279, 3: 349},
        "upsell_price": 99,
        "complementary": "tranexamic-niacinamide-serum",
    },
}

UPSELL_PRICE_AED = 99
