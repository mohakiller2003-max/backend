import logging
from dataclasses import dataclass
from typing import Optional

import geoip2.webservice

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class GeoIpResult:
    country_code: Optional[str]
    is_uae: bool


def lookup_country(ip: Optional[str]) -> GeoIpResult:
    if not ip or ip.startswith(("127.", "::1", "localhost")):
        return GeoIpResult(country_code=None, is_uae=True)

    if not settings.MAXMIND_ACCOUNT_ID or not settings.MAXMIND_LICENSE_KEY:
        return GeoIpResult(country_code=None, is_uae=True)

    try:
        client = geoip2.webservice.Client(
            settings.MAXMIND_ACCOUNT_ID,
            settings.MAXMIND_LICENSE_KEY,
            host="geolite.info",
        )
        code = client.country(ip).country.iso_code
        return GeoIpResult(country_code=code, is_uae=code == "AE")
    except Exception as exc:
        logger.warning("GeoIP lookup failed ip=%s error=%s", ip, exc)
        return GeoIpResult(country_code=None, is_uae=False)
