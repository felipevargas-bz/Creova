from creova.presentation import http


def test_webhook_secret_comparison_rejects_missing_secret() -> None:
    assert http.is_valid_webhook_secret("", "provided") is False
    assert http.is_valid_webhook_secret("expected", None) is False
    assert http.is_valid_webhook_secret("expected", "wrong") is False
    assert http.is_valid_webhook_secret("expected", "expected") is True
