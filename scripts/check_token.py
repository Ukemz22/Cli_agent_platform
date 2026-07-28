from core.db import SessionLocal
from core.models import Developer
from core.security import issue_token, hash_token

db = SessionLocal()
try:
    dev = Developer(telegram_chat_id=111222333)
    db.add(dev)
    db.flush()

    raw = issue_token(db, dev)
    print("raw token:", raw)
    print("status:", dev.status)
    print("hash matches stored:", dev.token_hash == hash_token(raw))
finally:
    db.rollback()
    db.close()
