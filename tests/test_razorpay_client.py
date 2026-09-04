import pytest
from src.razorpay_integration.client import RazorpayTestClient


@pytest.fixture
def client():
    # No key set -> _client stays None, but fingerprint extraction is pure
    # logic and needs no network access.
    return RazorpayTestClient(key_id="", key_secret="")


def test_card_fingerprint(client):
    payment = {"id": "pay_abc123", "method": "card",
               "card": {"id": "card_XYZ789"}, "email": "a@example.com"}
    fp = client.extract_fingerprint(payment)
    assert fp.instrument_id == "card_XYZ789"
    assert fp.method == "card"


def test_upi_fingerprint(client):
    payment = {"id": "pay_def456", "method": "upi", "vpa": "someone@okhdfcbank"}
    fp = client.extract_fingerprint(payment)
    assert fp.instrument_id == "someone@okhdfcbank"
    assert fp.method == "upi"


def test_same_card_different_identity_same_fingerprint(client):
    """The core fraud signal: two payments with different email/contact but
    the same underlying card must resolve to the same instrument id."""
    p1 = {"id": "pay_1", "method": "card", "card": {"id": "card_SHARED"}, "email": "fake1@mail.com"}
    p2 = {"id": "pay_2", "method": "card", "card": {"id": "card_SHARED"}, "email": "fake2@mail.com"}
    fp1 = client.extract_fingerprint(p1)
    fp2 = client.extract_fingerprint(p2)
    assert fp1.instrument_id == fp2.instrument_id
    assert fp1.email != fp2.email


def test_rejects_live_keys():
    with pytest.raises(RuntimeError):
        RazorpayTestClient(key_id="rzp_live_shouldfail", key_secret="x")


def test_accepts_test_keys():
    c = RazorpayTestClient(key_id="rzp_test_abc", key_secret="x")
    assert c.key_id.startswith("rzp_test_")
