from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_ENV: str = "production"
    API_BASE_URL: str = "https://api.skinouva.shop"
    FRONTEND_BASE_URL: str = "https://skinouva.shop"
    DATABASE_URL: str = ""

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if isinstance(value, str) and value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql://", 1)
        return value
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

    ORDER_WEBHOOK_TIMEOUT_SECONDS: int = 8
    LOG_LEVEL: str = "info"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()


# Server-side product and pricing constants — backend is the source of truth.
PRODUCT_CATALOG = {
    "tranexamic-niacinamide-serum": {
        "id": "tranexamic-niacinamide-serum",
        "name_ar": "سيروم الترانيكساميك + النياسيناميد ضد البقع الداكنة وتفاوت لون البشرة",
        "name_en": "Tranexamic + Niacinamide Dark Spot Serum",
        "offers": {1: 199, 2: 279, 3: 349},
        "upsell_price": 99,
        "complementary": "azelaic-acne-marks-serum",
    },
    "azelaic-acne-marks-serum": {
        "id": "azelaic-acne-marks-serum",
        "name_ar": "سيروم الأزيليك لحب الشباب الهرموني وآثاره",
        "name_en": "Azelaic Serum for Hormonal Acne and Marks",
        "offers": {1: 199, 2: 279, 3: 349},
        "upsell_price": 99,
        "complementary": "tranexamic-niacinamide-serum",
    },
}

UPSELL_PRICE_AED = 99
