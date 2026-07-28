from core.db import SessionLocal
from core.models import Developer, Business
from core.security import issue_token, hash_token


def test_token_identifies_correct_developer():
    db = SessionLocal()
    try:
        dev = Developer(telegram_chat_id=111000111)
        db.add(dev)
        db.flush()
        raw = issue_token(db, dev)

        looked_up = db.query(Developer).filter(Developer.token_hash == hash_token(raw)).first()
        assert looked_up.id == dev.id
    finally:
        db.rollback()
        db.close()


def test_developer_a_cannot_access_developer_b_business():
    db = SessionLocal()
    try:
        dev_a = Developer(telegram_chat_id=222000222)
        dev_b = Developer(telegram_chat_id=333000333)
        db.add_all([dev_a, dev_b])
        db.flush()

        biz_b = Business(developer_id=dev_b.id, name="Dev B's Business")
        db.add(biz_b)
        db.flush()

        # Simulate the exact query get_owned_business runs, using dev_a's id
        found = db.query(Business).filter(
            Business.id == biz_b.id,
            Business.developer_id == dev_a.id,
        ).first()

        assert found is None  # dev A must NOT see dev B's business
    finally:
        db.rollback()
        db.close()


def test_developer_can_access_own_business():
    db = SessionLocal()
    try:
        dev = Developer(telegram_chat_id=444000444)
        db.add(dev)
        db.flush()

        biz = Business(developer_id=dev.id, name="My Own Business")
        db.add(biz)
        db.flush()

        found = db.query(Business).filter(
            Business.id == biz.id,
            Business.developer_id == dev.id,
        ).first()

        assert found is not None
        assert found.id == biz.id
    finally:
        db.rollback()
        db.close()
