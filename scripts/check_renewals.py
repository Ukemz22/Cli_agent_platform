"""
Chapter 6, Part C: monthly renewal check.
Finds developers whose subscription lapsed more than 7 days ago,
flags them past_due, and sends a fresh Paystack payment link via Telegram.

Run manually or on a schedule (cron / Replit scheduled task):
  python3 scripts/check_renewals.py
"""
from datetime import datetime, timedelta, timezone

from core.db import SessionLocal
from core.models import Developer
from core.paystack import initialize_transaction
from core.telegram import send_telegram_message

GRACE_PERIOD_DAYS = 7
RENEWAL_AMOUNT_KOBO = 10000  # ₦100, same as initial signup


def check_renewals():
    db = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=GRACE_PERIOD_DAYS)

        lapsed = (
            db.query(Developer)
            .filter(Developer.status == "active")
            .filter(Developer.subscription_expires_at.isnot(None))
            .filter(Developer.subscription_expires_at < cutoff)
            .all()
        )

        for developer in lapsed:
            developer.status = "past_due"

            email = f"dev{developer.telegram_chat_id}@cliagentplatform.dev"
            payment = initialize_transaction(
                email=email,
                amount_kobo=RENEWAL_AMOUNT_KOBO,
                metadata={"developer_id": str(developer.id), "renewal": True},
            )
            pay_link = payment["data"]["authorization_url"]

            send_telegram_message(
                developer.telegram_chat_id,
                f"Your subscription has lapsed. Renew now to keep your agents active:\n{pay_link}",
            )

        db.commit()
        print(f"Checked renewals: {len(lapsed)} developer(s) flagged past_due and notified.")

    finally:
        db.close()


if __name__ == "__main__":
    check_renewals()
