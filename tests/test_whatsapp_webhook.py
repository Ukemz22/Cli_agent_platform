"""
Tests for the WhatsApp webhook receiver (Chapter 5).
Covers: GET verify handshake, signature verification, business routing
by phone_number_id, tenant isolation, and payload parsing.
"""
import hashlib
import hmac
import json
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from api.main import app
from core.config import settings
from core.db import SessionLocal
from core.models import Developer, Business
from api.routes_whatsapp import parse_incoming_message, _find_business_by_phone_number_id

client = TestClient(app)


def _sign(body: bytes) -> str:
    digest = hmac.new(settings.whatsapp_app_secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def test_verify_webhook_success():
    resp = client.get("/webhooks/whatsapp", params={
        "hub.mode": "subscribe",
        "hub.verify_token": settings.whatsapp_verify_token,
        "hub.challenge": "12345",
    })
    assert resp.status_code == 200
    assert resp.text == "12345"


def test_verify_webhook_wrong_token():
    resp = client.get("/webhooks/whatsapp", params={
        "hub.mode": "subscribe",
        "hub.verify_token": "wrong-token",
        "hub.challenge": "12345",
    })
    assert resp.status_code == 403


def test_receive_webhook_rejects_missing_signature():
    payload = {"entry": [{"changes": [{"value": {"messages": []}}]}]}
    resp = client.post("/webhooks/whatsapp", json=payload)
    assert resp.status_code == 403


def test_receive_webhook_rejects_invalid_signature():
    body = json.dumps({"entry": []}).encode()
    resp = client.post(
        "/webhooks/whatsapp",
        content=body,
        headers={"X-Hub-Signature-256": "sha256=deadbeef", "Content-Type": "application/json"},
    )
    assert resp.status_code == 403


def test_parse_incoming_message_extracts_text():
    payload = {
        "entry": [{"changes": [{"value": {
            "metadata": {"phone_number_id": "1112223333"},
            "messages": [{"from": "2348000000000", "type": "text", "text": {"body": "hi"}}],
        }}]}]
    }
    result = parse_incoming_message(payload)
    assert result == {"phone_number_id": "1112223333", "from": "2348000000000", "text": "hi"}


def test_parse_incoming_message_ignores_status_updates():
    payload = {"entry": [{"changes": [{"value": {"statuses": [{"status": "delivered"}]}}]}]}
    assert parse_incoming_message(payload) is None


def test_find_business_by_phone_number_id_matches():
    db = SessionLocal()
    try:
        dev = Developer(telegram_chat_id=900100200)
        db.add(dev)
        db.flush()

        biz = Business(developer_id=dev.id, name="wa-test-bakery", status="active",
                        system_prompt="You are a test assistant.",
                        channels_config={"whatsapp": {"phone_number_id": "1112223333"}})
        db.add(biz)
        db.flush()

        found = _find_business_by_phone_number_id(db, "1112223333")
        assert found is not None
        assert found.id == biz.id
    finally:
        db.rollback()
        db.close()


def test_find_business_by_phone_number_id_no_match():
    db = SessionLocal()
    try:
        dev = Developer(telegram_chat_id=900100201)
        db.add(dev)
        db.flush()

        biz = Business(developer_id=dev.id, name="wa-test-bakery-2", status="active",
                        system_prompt="You are a test assistant.",
                        channels_config={"whatsapp": {"phone_number_id": "1112223333"}})
        db.add(biz)
        db.flush()

        found = _find_business_by_phone_number_id(db, "9999999999")
        assert found is None
    finally:
        db.rollback()
        db.close()


def test_two_businesses_route_to_correct_one():
    """Critical multi-tenant check: business A's number must never resolve to business B."""
    db = SessionLocal()
    try:
        dev = Developer(telegram_chat_id=900100202)
        db.add(dev)
        db.flush()

        biz_a = Business(developer_id=dev.id, name="wa-biz-a", status="active",
                          system_prompt="a", channels_config={"whatsapp": {"phone_number_id": "1111111111"}})
        biz_b = Business(developer_id=dev.id, name="wa-biz-b", status="active",
                          system_prompt="b", channels_config={"whatsapp": {"phone_number_id": "2222222222"}})
        db.add(biz_a)
        db.add(biz_b)
        db.flush()

        found_a = _find_business_by_phone_number_id(db, "1111111111")
        found_b = _find_business_by_phone_number_id(db, "2222222222")

        assert found_a.id == biz_a.id
        assert found_b.id == biz_b.id
        assert found_a.id != found_b.id
    finally:
        db.rollback()
        db.close()


@patch("api.routes_whatsapp.httpx.post")
@patch("api.routes_whatsapp.get_llm_for_business")
def test_receive_webhook_full_flow_sends_reply(mock_get_llm, mock_post):
    from core.llm_provider import LLMResponse

    db = SessionLocal()
    try:
        dev = Developer(telegram_chat_id=900100203)
        db.add(dev)
        db.flush()

        biz = Business(developer_id=dev.id, name="wa-full-flow", status="active",
                        system_prompt="You are a test assistant.",
                        channels_config={"whatsapp": {"phone_number_id": "1112223333"}})
        db.add(biz)
        db.commit()

        fake_llm = MagicMock()
        fake_llm.complete.return_value = LLMResponse(reply_text="We sell bread!")
        mock_get_llm.return_value = fake_llm
        mock_post.return_value = MagicMock(status_code=200, text="ok")

        payload = {
            "entry": [{"changes": [{"value": {
                "metadata": {"phone_number_id": "1112223333"},
                "messages": [{"from": "2348000000000", "type": "text", "text": {"body": "do you sell bread?"}}],
            }}]}]
        }
        body = json.dumps(payload).encode()

        resp = client.post(
            "/webhooks/whatsapp",
            content=body,
            headers={"X-Hub-Signature-256": _sign(body), "Content-Type": "application/json"},
        )

        assert resp.status_code == 200
        mock_post.assert_called_once()
    finally:
        db.rollback()
        db.close()


@patch("api.routes_whatsapp.get_llm_for_business")
def test_receive_webhook_no_business_found(mock_get_llm):
    payload = {
        "entry": [{"changes": [{"value": {
            "metadata": {"phone_number_id": "0000000000"},
            "messages": [{"from": "2348000000000", "type": "text", "text": {"body": "hi"}}],
        }}]}]
    }
    body = json.dumps(payload).encode()

    resp = client.post(
        "/webhooks/whatsapp",
        content=body,
        headers={"X-Hub-Signature-256": _sign(body), "Content-Type": "application/json"},
    )

    assert resp.status_code == 200
    mock_get_llm.assert_not_called()
