from core.db import SessionLocal
from core.models import Developer

db = SessionLocal()
dev = db.query(Developer).filter(Developer.telegram_chat_id == 444555666).first()
if dev:
    db.delete(dev)
    db.commit()
    print("cleaned up")
else:
    print("nothing to clean")
db.close()
