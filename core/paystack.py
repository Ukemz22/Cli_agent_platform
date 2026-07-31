"""
Minimal Paystack wrapper: initialize a transaction (get a payment link),
and verify inbound webhook signatures.
"""
import hashlib
import hmac

import httpx

from core.config import settings

PAYSTACK_BASE_URL = "https://api.paystack.co"


def initialize_transaction(email: str, amount_kobo: int, metadata: dict) -> dict:
    """
    Create a Paystack payment session. amount_kobo is in kobo (₦100 = 10000).
    Returns Paystack's response, including data.authorization_url (the payment link).
    """
    resp = httpx.post(
        f"{PAYSTACK_BASE_URL}/transaction/initialize",
        headers={"Authorization": f"Bearer {settings.paystack_secret_key}"},
        json={"email": email, "amount": amount_kobo, "metadata": metadata},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def verify_paystack_signature(raw_body: bytes, signature_header: str | None) -> bool:
    """Paystack signs webhooks with HMAC-SHA512 of the raw body using the secret key."""
    if not signature_header:
        return False
    expected = hmac.new(
        settings.paystack_secret_key.encode(), raw_body, hashlib.sha512
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)
