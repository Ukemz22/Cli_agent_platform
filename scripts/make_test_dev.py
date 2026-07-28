from core.db import SessionLocal
from core.models import Developer
from core.security import issue_token

TEST_CHAT_ID = 444555666

db = SessionLocal()
dev = db.query(Developer).filter(Developer.telegram_chat_id == TEST_CHAT_ID).first()
if dev is None:
    dev = Developer(telegram_chat_id=TEST_CHAT_ID)
    db.add(dev)
    db.flush()

raw = issue_token(db, dev)
db.commit()
print(raw)
db.close()
