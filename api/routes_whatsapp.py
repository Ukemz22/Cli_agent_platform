import hashlib
import hmac

import httpx
from fastapi import APIRouter, Query, HTTPException, Request, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from core.config import settings
from core.db import get_db
from core.models import Business
from core.agent_runtime import run_agent_turn
from core.llm_factory import get_llm_for_business

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
    """HMAC-SHA256 check using hmac.compare_digest (timing-safe, Rule 3)."""
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected_hash = signature_header.removeprefix("sha256=")
    computed_hash = hmac.new(
        settings.whatsapp_app_secret.encode(), raw_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(computed_hash, expected_hash)


def _find_business_by_phone_number_id(db: Session, phone_number_id: str) -> Business | None:
    """
    Find the business whose channels_config["whatsapp"]["phone_number_id"]
    matches the incoming webhook. Filters in Python — there are few businesses
    per deployment so a full scan is acceptable here.
    """
    businesses = db.query(Business).filter(Business.status.in_(["active", "live"])).all()
    for b in businesses:
        if (
            isinstance(b.channels_config, dict)
            and b.channels_config.get("whatsapp", {}).get("phone_number_id") == phone_number_id
        ):
            return b
    return None


def _send_whatsapp_reply(phone_number_id: str, to: str, text: str) -> None:
    """
    Send a text reply to the customer via the WhatsApp Cloud API.
    Raises HTTPException(502) if Meta's API returns a non-2xx status.
    """
    url = f"https://graph.facebook.com/v19.0/{phone_number_id}/messages"
    resp = httpx.post(
        url,
        json={
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": text},
        },
        headers={"Authorization": f"Bearer {settings.whatsapp_access_token}"},
        timeout=10.0,
    )
    if resp.status_code not in (200, 201):
        raise HTTPException(
            status_code=502,
            detail=f"WhatsApp send failed: {resp.status_code} {resp.text}",
        )


@router.post("")
async def receive_webhook(request: Request, db: Session = Depends(get_db)):
    raw_body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")

    if not _verify_signature(raw_body, signature):
        raise HTTPException(status_code=403, detail="Invalid signature")

    payload = await request.json()
    parsed = parse_incoming_message(payload)

    if parsed is None:
        # Status updates, delivery receipts, etc. — acknowledge and ignore
        return {"status": "ignored"}

    business = _find_business_by_phone_number_id(db, parsed["phone_number_id"])
    if business is None:
        # No business registered for this phone number — acknowledge Meta but don't process
        return {"status": "no_business_found"}

    llm = get_llm_for_business(business)
    result = run_agent_turn(
        db=db,
        business=business,
        customer_message=parsed["text"],
        llm=llm,
        channel="whatsapp",
        customer_id=parsed["from"],
    )
    db.commit()

    _send_whatsapp_reply(
        phone_number_id=parsed["phone_number_id"],
        to=parsed["from"],
        text=result.reply_text,
    )

    return {"status": "sent", "escalated": result.escalated}


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
