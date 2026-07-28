from core.db import SessionLocal
from core.models import Developer, Business
from core.schemas import BusinessRead

db = SessionLocal()
try:
    dev = Developer(telegram_chat_id=999888777)
    db.add(dev)
    db.flush()

    biz = Business(developer_id=dev.id, name="Schema Test Co", system_prompt="You are helpful.")
    db.add(biz)
    db.flush()

    schema = BusinessRead.model_validate(biz)
    print(schema.model_dump_json(indent=2))
finally:
    db.rollback()
    db.close()
