from pydantic import SecretStr

from creova.logging import REDACTED, redact


def test_redacts_sensitive_keys_recursively() -> None:
    event = {
        "authorization": "Bearer real-token",
        "headers": {
            "x-telegram-bot-api-secret-token": "webhook-secret",
            "content-type": "application/json",
        },
        "database_url": "postgresql://user:password@localhost/db",
        "provider": {
            "google_api_key": "google-key",
            "signed_url": "https://example.test/private?signature=value",
        },
        "safe": "visible",
    }

    redacted = redact(event)

    assert redacted["authorization"] == REDACTED
    assert redacted["headers"]["x-telegram-bot-api-secret-token"] == REDACTED
    assert redacted["headers"]["content-type"] == "application/json"
    assert redacted["database_url"] == REDACTED
    assert redacted["provider"]["google_api_key"] == REDACTED
    assert redacted["provider"]["signed_url"] == REDACTED
    assert redacted["safe"] == "visible"


def test_redacts_secret_values_without_sensitive_keys() -> None:
    assert redact({"value": SecretStr("real-secret")}) == {"value": REDACTED}
