"""
Tests for Chapter 6: Telegram onboarding + Paystack billing.
"""
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from api.main import app
from core.db import SessionLocal
from core.models import Developer
from core.paystack import verify_paystack_signature
from scripts.check_renewals import check_renewals

client = TestClient(app)


def _sign_paystack(body: bytes, secret: str) -> str:
    import hashlib, hmac
    return hmac.new(secret.encode(), body, hashlib.sha512).hexdigest()


def test_verify_paystack_signature_valid():
    from core.config import settings
    body = b'{"event": "charge.success"}'
    sig = _sign_paystack(body, settings.paystack_secret_key)
    assert verify_paystack_signature(body, sig) is True


def test_verify_paystack_signature_invalid():
    body = b'{"event": "charge.success"}'
    assert verify_paystack_signature(body, "wrong-signature") is False


def test_verify_paystack_signature_missing():
    body = b'{"event": "charge.success"}'
    assert verify_paystack_signature(body, None) is False


@patch("api.routes_telegram.initialize_transaction")
@patch("api.routes_telegram.send_telegram_message")
def test_telegram_start_creates_developer_and_sends_link(mock_send, mock_init):
    mock_init.return_value = {"data": {"authorization_url": "https://checkout.paystack.com/fake123"}}

    payload = {"message": {"chat": {"id": 700100200}, "text": "/start"}}
    resp = client.post("/webhooks/telegram", json=payload)

    assert resp.status_code == 200
    assert resp.json()["status"] == "payment_link_sent"
    mock_send.assert_called_once()

    db = SessionLocal()
    try:
        dev = db.query(Developer).filter(Developer.telegram_chat_id == 700100200).first()
        assert dev is not None
        assert dev.status == "pending"
    finally:
        db.rollback()
        db.close()


@patch("api.routes_paystack.send_telegram_message")
def test_paystack_webhook_issues_token_on_success(mock_send):
    from core.config import settings

    db = SessionLocal()
    try:
        dev = Developer(telegram_chat_id=700100201, status="pending")
        db.add(dev)
        db.commit()
        dev_id = str(dev.id)
    finally:
        db.close()

    payload = {
        "event": "charge.success",
        "data": {
            "amount": 10000,
            "reference": "test_ref_123",
            "metadata": {"developer_id": dev_id},
        },
    }
    body = json.dumps(payload).encode()
    sig = _sign_paystack(body, settings.paystack_secret_key)

    resp = client.post(
        "/webhooks/paystack",
        content=body,
        headers={"x-paystack-signature": sig, "Content-Type": "application/json"},
    )

    assert resp.status_code == 200
    assert resp.json()["status"] == "activated"
    mock_send.assert_called_once()

    db = SessionLocal()
    try:
        dev = db.query(Developer).filter(Developer.id == dev_id).first()
        assert dev.status == "active"
        assert dev.token_hash is not None
        assert dev.subscription_expires_at is not None
    finally:
        db.rollback()
        db.close()


def test_paystack_webhook_rejects_bad_signature():
    payload = {"event": "charge.success", "data": {}}
    body = json.dumps(payload).encode()
    resp = client.post(
        "/webhooks/paystack",
        content=body,
        headers={"x-paystack-signature": "bad-sig", "Content-Type": "application/json"},
    )
    assert resp.status_code == 403


def test_paystack_webhook_unknown_developer():
    from core.config import settings

    payload = {
        "event": "charge.success",
        "data": {"amount": 10000, "reference": "ref", "metadata": {"developer_id": "00000000-0000-0000-0000-000000000000"}},
    }
    body = json.dumps(payload).encode()
    sig = _sign_paystack(body, settings.paystack_secret_key)

    resp = client.post(
        "/webhooks/paystack",
        content=body,
        headers={"x-paystack-signature": sig, "Content-Type": "application/json"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "no_developer_found"


@patch("scripts.check_renewals.send_telegram_message")
@patch("scripts.check_renewals.initialize_transaction")
def test_check_renewals_flags_lapsed_developer(mock_init, mock_send):
    mock_init.return_value = {"data": {"authorization_url": "https://checkout.paystack.com/renew123"}}

    db = SessionLocal()
    try:
        lapsed_dev = Developer(
            telegram_chat_id=700100202,
            status="active",
            subscription_expires_at=datetime.now(timezone.utc) - timedelta(days=10),
        )
        fresh_dev = Developer(
            telegram_chat_id=700100203,
            status="active",
            subscription_expires_at=datetime.now(timezone.utc) + timedelta(days=20),
        )
        db.add(lapsed_dev)
        db.add(fresh_dev)
        db.commit()
        lapsed_id = lapsed_dev.id
        fresh_id = fresh_dev.id
    finally:
        db.close()

    check_renewals()

    db = SessionLocal()
    try:
        lapsed_dev = db.query(Developer).filter(Developer.id == lapsed_id).first()
        fresh_dev = db.query(Developer).filter(Developer.id == fresh_id).first()
        assert lapsed_dev.status == "past_due"
        assert fresh_dev.status == "active"
    finally:
        db.rollback()
        db.close()

    mock_send.assert_called()
