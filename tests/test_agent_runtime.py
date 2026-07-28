from core.db import SessionLocal
from core.models import Developer, Business, KnowledgeDoc, Conversation, Message
from core.agent_runtime import run_agent_turn
from core.llm_provider import FakeLLMProvider, LLMResponse


def test_happy_path_full_loop():
    db = SessionLocal()
    try:
        dev = Developer(telegram_chat_id=100200300)
        db.add(dev)
        db.flush()

        biz = Business(developer_id=dev.id, name="Solar Co", status="active", system_prompt="You are a solar assistant.")
        db.add(biz)
        db.flush()

        doc = KnowledgeDoc(business_id=biz.id, filename="pricing.md", content="Solar panels cost 500000 naira.")
        db.add(doc)
        db.flush()

        fake = FakeLLMProvider(responses=[LLMResponse(reply_text="It costs 500000 naira.")])
        result = run_agent_turn(db, biz, "how much are solar panels", fake, channel="widget", customer_id="c1")

        assert result.reply_text == "It costs 500000 naira."
        assert result.escalated is False

        convo = db.query(Conversation).filter(Conversation.business_id == biz.id).first()
        assert convo is not None
        assert convo.status == "ai_active"

        messages = db.query(Message).filter(Message.conversation_id == convo.id).all()
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[1].role == "assistant"
    finally:
        db.rollback()
        db.close()


def test_paused_business_does_not_call_llm():
    db = SessionLocal()
    try:
        dev = Developer(telegram_chat_id=100200301)
        db.add(dev)
        db.flush()

        biz = Business(developer_id=dev.id, name="Paused Co", status="paused")
        db.add(biz)
        db.flush()

        fake = FakeLLMProvider(responses=[LLMResponse(reply_text="should not be used")])
        result = run_agent_turn(db, biz, "hello", fake)

        assert result.reply_text == "This service is currently paused."
        assert len(fake.calls) == 0  # LLM must NOT be called for a paused business
    finally:
        db.rollback()
        db.close()


def test_escalation_triggers_on_empty_retrieval_plus_phrase():
    db = SessionLocal()
    try:
        dev = Developer(telegram_chat_id=100200302)
        db.add(dev)
        db.flush()

        biz = Business(developer_id=dev.id, name="No Knowledge Co", status="active", system_prompt="You are helpful.")
        db.add(biz)
        db.flush()
        # deliberately NO knowledge docs — retrieval will be empty

        fake = FakeLLMProvider(responses=[LLMResponse(reply_text="should not be used")])
        result = run_agent_turn(db, biz, "I want to talk to a human", fake, channel="widget", customer_id="c2")

        assert result.escalated is True
        assert len(fake.calls) == 0  # LLM must NOT be called once escalation triggers

        convo = db.query(Conversation).filter(Conversation.business_id == biz.id).first()
        assert convo.status == "needs_human"

        messages = db.query(Message).filter(Message.conversation_id == convo.id).all()
        assert len(messages) == 2
        assert "team" in messages[1].content.lower()
    finally:
        db.rollback()
        db.close()


def test_no_escalation_when_knowledge_exists_even_with_phrase():
    """Escalation needs BOTH empty retrieval AND escalation language — not either alone."""
    db = SessionLocal()
    try:
        dev = Developer(telegram_chat_id=100200303)
        db.add(dev)
        db.flush()

        biz = Business(developer_id=dev.id, name="Has Knowledge Co", status="active", system_prompt="You are helpful.")
        db.add(biz)
        db.flush()

        doc = KnowledgeDoc(business_id=biz.id, filename="refunds.md", content="talk to a human refund policy explained here")
        db.add(doc)
        db.flush()

        fake = FakeLLMProvider(responses=[LLMResponse(reply_text="Here's our refund policy...")])
        result = run_agent_turn(db, biz, "talk to a human about refund policy", fake, channel="widget", customer_id="c3")

        assert result.escalated is False
        assert len(fake.calls) == 1  # LLM WAS called, since knowledge was found
    finally:
        db.rollback()
        db.close()
