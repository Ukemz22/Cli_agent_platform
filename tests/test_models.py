from core.db import SessionLocal
from core.models import Developer, Business


def test_business_belongs_to_developer():
    db = SessionLocal()
    try:
        dev = Developer(telegram_chat_id=123456789)
        db.add(dev)
        db.flush()  # assigns dev.id without committing

        biz = Business(developer_id=dev.id, name="Test Biz")
        db.add(biz)
        db.flush()

        assert biz.developer_id == dev.id
    finally:
        db.rollback()  # never leave test data in the real database
        db.close()


def test_cascade_delete_removes_business():
    db = SessionLocal()
    try:
        dev = Developer(telegram_chat_id=987654321)
        db.add(dev)
        db.flush()

        biz = Business(developer_id=dev.id, name="Cascade Test Biz")
        db.add(biz)
        db.flush()
        biz_id = biz.id

        db.delete(dev)
        db.flush()
        db.expire_all()  # forget cached objects, force a real DB read next

        still_there = db.get(Business, biz_id)
        assert still_there is None
    finally:
        db.rollback()
        db.close()
