from core.db import SessionLocal
from core.models import Developer
from core.security import issue_token

db = SessionLocal()
dev = Developer(telegram_chat_id=444555666)
db.add(dev)
db.flush()
raw = issue_token(db, dev)
db.commit()  # this one we KEEP, so /whoami can find it
print(raw)
db.close()
