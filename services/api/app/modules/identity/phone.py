import re

from app.modules.identity.errors import InvalidPhoneError

_INDIA_MOBILE = re.compile(r"^(?:\+91|91|0)?([6-9]\d{9})$")


def normalize_phone(raw: str) -> str:
    cleaned = re.sub(r"[\s\-()]", "", raw)
    match = _INDIA_MOBILE.match(cleaned)
    if match is None:
        raise InvalidPhoneError("Invalid Indian mobile number")
    return f"+91{match.group(1)}"
