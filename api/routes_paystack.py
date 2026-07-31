"""
Paystack payment webhook (Chapter 6, Part B).
On charge.success: issues a developer token, records the billing event,
sends the token via Telegram.
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Request, HTTPException

from core.db import SessionLocal
from core.models import Developer, BillingEvent
from core.paystack import verify_paystack_signature
from core.security import issue_token
from core.telegram import send_telegram_message

router = APIRouter()


@router.post("/webhooks/paystack")
async def receive_paystack_webhook(request: Request):
    raw_body = await request.body()
    signature = request.headers.get("x-paystack-signature")

    if not verify_paystack_signature(raw_body, signature):
        raise HTTPException(status_code=403, detail="Invalid Paystack signature")

    payload = await request.json()
    event = payload.get("event")

    if event != "charge.success":
        return {"status": "ignored_event", "event": event}

    data = payload["data"]
    metadata = data.get("metadata", {})
    developer_id = metadata.get("developer_id")

    db = SessionLocal()
    try:
        developer = db.query(Developer).filter(Developer.id == developer_id).first()
        if developer is None:
            return {"status": "no_developer_found"}

        raw_token = issue_token(db, developer)
        developer.subscription_expires_at = datetime.now(timezone.utc) + timedelta(days=30)

        billing_event = BillingEvent(
            developer_id=developer.id,
            event_type="payment_success",
            amount=data.get("amount"),
            paystack_ref=data.get("reference"),
        )
        db.add(billing_event)
        db.commit()

        send_telegram_message(
            developer.telegram_chat_id,
            f"Payment confirmed! Your CLI login token:\n\n{raw_token}\n\n"
            f"Run this once:\nplatform login --token {raw_token}",
        )
        return {"status": "activated"}
    finally:
        db.close()
