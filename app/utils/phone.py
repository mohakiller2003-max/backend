import re


class InvalidPhoneError(ValueError):
    pass


def normalize_uae_phone(raw: str) -> str:
    """
    Normalize a UAE mobile phone number to E.164 format: +9715XXXXXXXX.

    Accepted input formats:
        05XXXXXXXX         (10 digits, starts with 05)
        9715XXXXXXXX       (12 digits, starts with 9715)
        +9715XXXXXXXX      (13 chars, starts with +9715)

    Returns the normalized E.164 string or raises InvalidPhoneError.
    """
    if not raw:
        raise InvalidPhoneError("Phone number is required.")

    cleaned = re.sub(r"[\s\-\(\)\.]+", "", raw)

    if cleaned.startswith("+"):
        digits_only = cleaned[1:]
    else:
        digits_only = cleaned

    if re.match(r"^05\d{8}$", digits_only):
        # 05XXXXXXXX -> +9715XXXXXXXX
        return "+971" + digits_only[1:]

    if re.match(r"^9715\d{8}$", digits_only):
        # 9715XXXXXXXX -> +9715XXXXXXXX
        return "+" + digits_only

    if re.match(r"^9715\d{8}$", cleaned.lstrip("+")):
        return "+" + cleaned.lstrip("+")

    raise InvalidPhoneError(
        "Invalid UAE phone number. Expected format: 05XXXXXXXX or +9715XXXXXXXX."
    )


def meta_hash_phone(phone_e164: str) -> str:
    """SHA-256 hex of digits-only phone (no + prefix) for Meta CAPI."""
    import hashlib

    normalized = re.sub(r"[^\d]", "", phone_e164)
    return hashlib.sha256(normalized.encode()).hexdigest()


def tiktok_hash_phone(phone_e164: str) -> str:
    """SHA-256 hex of E.164 phone (with +) for TikTok Events API."""
    import hashlib

    return hashlib.sha256(phone_e164.encode()).hexdigest()


def snap_hash_phone(phone_e164: str) -> str:
    """SHA-256 hex of digits-only phone (no + prefix) for Snapchat CAPI."""
    import hashlib

    normalized = re.sub(r"[^\d]", "", phone_e164)
    return hashlib.sha256(normalized.encode()).hexdigest()
