"""
Telegram bot webhook (Chapter 6, Part A).
Handles /start: finds or creates a Developer, sends them a Paystack payment link.
"""
from fastapi import APIRouter, Request

from core.db import SessionLocal
from core.models import Developer
from core.paystack import initialize_transaction
from core.telegram import send_telegram_message

router = APIRouter()


@router.post("/webhooks/telegram")
async def receive_telegram_update(request: Request):
    body = await request.json()
    message = body.get("message")
    if not message:
        return {"status": "ignored_no_message"}

    chat_id = message["chat"]["id"]
    text = message.get("text", "")

    db = SessionLocal()
    try:
        developer = db.query(Developer).filter(Developer.telegram_chat_id == chat_id).first()

        if text.strip() == "/start":
            if developer is None:
                developer = Developer(telegram_chat_id=chat_id, status="pending")
                db.add(developer)
                db.flush()

            if developer.status == "active":
                send_telegram_message(
                    chat_id,
                    "You're already active! Run `platform login --token <your token>` in your CLI.",
                )
                db.commit()
                return {"status": "already_active"}

            amount_kobo = 10000  # ₦100
            email = f"dev{chat_id}@cliagentplatform.dev"
            payment = initialize_transaction(
                email=email,
                amount_kobo=amount_kobo,
                metadata={"developer_id": str(developer.id)},
            )
            pay_link = payment["data"]["authorization_url"]

            send_telegram_message(
                chat_id,
                f"Welcome! Pay ₦100 to activate your developer account:\n{pay_link}\n\n"
                "You'll get your CLI login token right here once payment is confirmed.",
            )
            db.commit()
            return {"status": "payment_link_sent"}

        return {"status": "ignored_unrecognized_text"}
    finally:
        db.close()
