import hashlib
import hmac
import json
import time
import unittest
from urllib.parse import urlencode

from mini_app_auth import verify_init_data

TOKEN = "123456:TEST-TOKEN"


def make_init_data(
    user_id: int = 1,
    username: str = "client",
    auth_date: int | None = None,
    token: str = TOKEN,
) -> str:
    values = {
        "auth_date": str(int(time.time()) if auth_date is None else auth_date),
        "query_id": "query-1",
        "user": json.dumps(
            {
                "id": user_id,
                "first_name": "Client",
                "username": username,
                "language_code": "uk",
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ),
    }
    check_string = "\n".join(f"{key}={value}" for key, value in sorted(values.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    values["hash"] = hmac.new(
        secret,
        check_string.encode(),
        hashlib.sha256,
    ).hexdigest()
    return urlencode(values)


class MiniAppAuthTests(unittest.TestCase):
    def test_valid_init_data(self) -> None:
        user = verify_init_data(make_init_data(), TOKEN)
        self.assertIsNotNone(user)
        self.assertEqual(user["id"], 1)
        self.assertEqual(user["username"], "client")

    def test_tampered_user_is_rejected(self) -> None:
        data = make_init_data()
        tampered = data.replace("Client", "Hacker")
        self.assertIsNone(verify_init_data(tampered, TOKEN))

    def test_wrong_bot_token_is_rejected(self) -> None:
        self.assertIsNone(verify_init_data(make_init_data(), "other-token"))

    def test_missing_or_malformed_data(self) -> None:
        self.assertIsNone(verify_init_data("", TOKEN))
        self.assertIsNone(verify_init_data("user=%7B%7D", TOKEN))
        self.assertIsNone(verify_init_data("auth_date=1&user=%7B%7D", TOKEN))

    def test_expired_and_future_auth_date(self) -> None:
        self.assertIsNone(
            verify_init_data(
                make_init_data(auth_date=int(time.time()) - 100000),
                TOKEN,
                max_age_seconds=3600,
            )
        )
        self.assertIsNone(
            verify_init_data(
                make_init_data(auth_date=int(time.time()) + 1000),
                TOKEN,
            )
        )


if __name__ == "__main__":
    unittest.main()
