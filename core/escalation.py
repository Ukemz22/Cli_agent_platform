"""
Escalation detection. Two triggers: retrieval came back empty,
OR the message itself signals the customer wants a human /
sounds frustrated. Keyword-based, per YAGNI (Rule 5) — a proper
classifier only if this proves too weak in real use.
"""

ESCALATION_PHRASES = [
    "talk to a human",
    "speak to a human",
    "real person",
    "customer care",
    "this is ridiculous",
    "not helpful",
    "useless",
    "i want a refund",
    "cancel my order",
    "speak to someone",
    "human agent",
]


def message_signals_escalation(message_text: str) -> bool:
    lowered = message_text.lower()
    return any(phrase in lowered for phrase in ESCALATION_PHRASES)


def should_escalate(knowledge_snippets: list[str], memory_snippets: list[str], message_text: str) -> bool:
    retrieval_empty = not knowledge_snippets and not memory_snippets
    return retrieval_empty and message_signals_escalation(message_text)
