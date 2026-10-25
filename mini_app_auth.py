import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl


def _secret_key(bot_token: str) -> bytes:
    return hmac.new(
        b"WebAppData",
        bot_token.encode("utf-8"),
        hashlib.sha256,
    ).digest()


def verify_init_data(
    init_data: str,
    bot_token: str,
    max_age_seconds: int = 86400,
    now: float | None = None,
) -> dict | None:
    """Validate Telegram Mini App initData and return its user.

    Implements Telegram's HMAC-SHA256 scheme. Never logs the raw initData.
    """
    if not init_data or not bot_token or len(init_data) > 8192:
        return None
    try:
        pairs = parse_qsl(init_data, keep_blank_values=True, strict_parsing=False)
    except ValueError:
        return None
    values = dict(pairs)
    received_hash = values.get("hash", "")
    if len(received_hash) != 64:
        return None

    check_string = "\n".join(
        f"{key}={value}"
        for key, value in sorted(pairs)
        if key != "hash"
    )
    expected = hmac.new(
        _secret_key(bot_token),
        check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, received_hash):
        return None

    try:
        auth_date = int(values["auth_date"])
    except (KeyError, ValueError):
        return None
    current = time.time() if now is None else now
    if auth_date > current + 300 or current - auth_date > max_age_seconds:
        return None

    try:
        user = json.loads(values["user"])
    except (KeyError, json.JSONDecodeError, TypeError):
        return None
    if not isinstance(user, dict):
        return None
    try:
        user_id = int(user["id"])
    except (KeyError, TypeError, ValueError):
        return None
    if user_id <= 0:
        return None
    user["id"] = user_id
    user["auth_date"] = auth_date
    return user
