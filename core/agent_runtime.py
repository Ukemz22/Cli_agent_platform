"""
The Agent Runtime — channel-agnostic "brain". Pure function/class,
no FastAPI, no WhatsApp (per Chapter 3 spec). Takes business_id +
customer message, returns a reply, persists conversation history.
"""
from dataclasses import dataclass
from sqlalchemy.orm import Session

from core.models import Business, Conversation, Message, MemoryFact
from core.knowledge import load_business_context
from core.escalation import should_escalate
from core.llm_provider import LLMProvider


@dataclass
class AgentResult:
    reply_text: str
    escalated: bool
    tool_used: str | None = None


CORRECTION_MARKERS = ["actually,", "correction:", "note for future:", "remember that"]


def _execute_tool(tool_call: dict) -> dict:
    name = tool_call.get("name")
    if name == "capture_lead":
        return {"status": "lead captured", "contact": tool_call.get("args", {}).get("contact")}
    return {"status": "unknown tool", "name": name}


def _get_or_create_conversation(db: Session, business: Business, channel: str, customer_id: str) -> Conversation:
    convo = db.query(Conversation).filter(
        Conversation.business_id == business.id,
        Conversation.channel == channel,
        Conversation.customer_id == customer_id,
        Conversation.status.in_(["ai_active", "human_active"]),
    ).first()
    if convo is None:
        convo = Conversation(business_id=business.id, channel=channel, customer_id=customer_id, status="ai_active")
        db.add(convo)
        db.flush()
    return convo


def _load_recent_history(db: Session, conversation_id, limit: int = 10) -> list[dict]:
    rows = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .limit(limit)
        .all()
    )
    return [{"role": m.role, "content": m.content} for m in rows]


def run_agent_turn(
    db: Session,
    business: Business,
    customer_message: str,
    llm: LLMProvider,
    channel: str = "test",
    customer_id: str = "test-customer",
) -> AgentResult:
    if business.status not in ("active", "live"):
        return AgentResult(reply_text="This service is currently paused.", escalated=False)

    convo = _get_or_create_conversation(db, business, channel, customer_id)
    db.add(Message(conversation_id=convo.id, role="user", content=customer_message))
    db.flush()

    ctx = load_business_context(db, business, customer_message)

    if should_escalate(ctx.knowledge_snippets, ctx.memory_snippets, customer_message):
        convo.status = "needs_human"
        db.add(convo)
        reply = "I've passed this to a member of our team — they'll follow up with you shortly."
        db.add(Message(conversation_id=convo.id, role="assistant", content=reply))
        db.flush()
        return AgentResult(reply_text=reply, escalated=True)

    final_prompt = _build_prompt(ctx)
    recent_history = _load_recent_history(db, convo.id)
    messages = recent_history + [{"role": "user", "content": customer_message}]

    llm_response = llm.complete(system_prompt=final_prompt, messages=messages)
    tool_used = None

    if llm_response.tool_call:
        tool_result = _execute_tool(llm_response.tool_call)
        messages.append({"role": "assistant", "content": f"[tool_call: {llm_response.tool_call}]"})
        messages.append({"role": "tool", "content": str(tool_result)})
        llm_response = llm.complete(system_prompt=final_prompt, messages=messages)
        tool_used = llm_response.tool_call.get("name") if llm_response.tool_call else "capture_lead"

    db.add(Message(conversation_id=convo.id, role="assistant", content=llm_response.reply_text))

    if any(marker in llm_response.reply_text.lower() for marker in CORRECTION_MARKERS):
        db.add(MemoryFact(business_id=business.id, fact_text=llm_response.reply_text, source="conversation"))

    db.flush()

    return AgentResult(reply_text=llm_response.reply_text, escalated=False, tool_used=tool_used)


def _build_prompt(ctx) -> str:
    parts = [ctx.system_prompt]
    if ctx.knowledge_snippets:
        parts.append("Relevant knowledge:\n" + "\n".join(ctx.knowledge_snippets))
    if ctx.memory_snippets:
        parts.append("Things learned from past corrections:\n" + "\n".join(ctx.memory_snippets))
    return "\n\n".join(parts)
