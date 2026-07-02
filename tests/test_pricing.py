import pytest
from decimal import Decimal

from app.core.config import PRODUCT_CATALOG, UPSELL_PRICE_AED


def test_product_catalog_prices():
    for product_id, product in PRODUCT_CATALOG.items():
        assert product["offers"][1] == 199
        assert product["offers"][2] == 279
        assert product["offers"][3] == 349
        assert product["upsell_price"] == 99


def test_upsell_price_constant():
    assert UPSELL_PRICE_AED == 99


def test_complementary_products():
    p1 = "tranexamic-niacinamide-serum"
    p2 = "azelaic-acne-marks-serum"
    assert PRODUCT_CATALOG[p1]["complementary"] == p2
    assert PRODUCT_CATALOG[p2]["complementary"] == p1


def test_invalid_offer_quantity():
    product = PRODUCT_CATALOG["tranexamic-niacinamide-serum"]
    assert 4 not in product["offers"]
    assert 0 not in product["offers"]


def test_all_products_have_required_fields():
    required_fields = {"id", "name_ar", "name_en", "offers", "upsell_price", "complementary"}
    for pid, product in PRODUCT_CATALOG.items():
        missing = required_fields - set(product.keys())
        assert not missing, f"{pid} missing fields: {missing}"
