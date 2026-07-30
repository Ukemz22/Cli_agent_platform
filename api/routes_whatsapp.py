import hashlib
import hmac

from fastapi import APIRouter, Query, HTTPException, Request
from fastapi.responses import PlainTextResponse
from core.config import settings

router = APIRouter(prefix="/webhooks/whatsapp", tags=["whatsapp"])


@router.get("")
async def verify_webhook(
    hub_mode: str = Query(alias="hub.mode"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge"),
):
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        return PlainTextResponse(hub_challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


def _verify_signature(raw_body: bytes, signature_header: str | None) -> bool:
    """HMAC-SHA256 check using hmac.compare_digest (timing-safe, standard library — Rule 3)."""
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected_hash = signature_header.removeprefix("sha256=")
    computed_hash = hmac.new(
        settings.whatsapp_app_secret.encode(), raw_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(computed_hash, expected_hash)


@router.post("")
async def receive_webhook(request: Request):
    raw_body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")

    if not _verify_signature(raw_body, signature):
        raise HTTPException(status_code=403, detail="Invalid signature")

    return {"status": "received"}

def parse_incoming_message(payload: dict) -> dict | None:
    """Extract {phone_number_id, from, text} from a WhatsApp webhook payload.
    Returns None if this event isn't an actual text message (e.g. status update)."""
    try:
        value = payload["entry"][0]["changes"][0]["value"]
        messages = value.get("messages")
        if not messages:
            return None
        message = messages[0]
        if message.get("type") != "text":
            return None
        return {
            "phone_number_id": value["metadata"]["phone_number_id"],
            "from": message["from"],
            "text": message["text"]["body"],
        }
    except (KeyError, IndexError):
        return None
