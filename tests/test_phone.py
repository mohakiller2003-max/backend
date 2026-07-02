import pytest
from app.utils.phone import normalize_uae_phone, InvalidPhoneError


@pytest.mark.parametrize("raw,expected", [
    ("0501234567", "+971501234567"),
    ("0551234567", "+971551234567"),
    ("971501234567", "+971501234567"),
    ("+971501234567", "+971501234567"),
    ("05 01 234 567", "+971501234567"),
    ("+971 50 123 4567", "+971501234567"),
])
def test_valid_uae_phones(raw, expected):
    assert normalize_uae_phone(raw) == expected


@pytest.mark.parametrize("raw", [
    "",
    "12345",
    "0401234567",    # starts with 04 (landline)
    "00971501234567",
    "9715012345",    # too short
    "abcdefghij",
    "0501234567890",  # too long
])
def test_invalid_uae_phones(raw):
    with pytest.raises(InvalidPhoneError):
        normalize_uae_phone(raw)
