"""
Loads a business's context (prompt + knowledge + memory) and
does simple keyword-based retrieval. Embeddings/vector search
only if this proves too weak later (YAGNI, Rule 5).
"""
from dataclasses import dataclass
from sqlalchemy.orm import Session

from core.models import Business, KnowledgeDoc, MemoryFact


@dataclass
class BusinessContext:
    system_prompt: str
    knowledge_snippets: list[str]
    memory_snippets: list[str]


def load_business_context(db: Session, business: Business, query_text: str) -> BusinessContext:
    docs = db.query(KnowledgeDoc).filter(KnowledgeDoc.business_id == business.id).all()
    facts = db.query(MemoryFact).filter(MemoryFact.business_id == business.id).all()

    knowledge_snippets = _keyword_search(query_text, [(d.content, d.filename) for d in docs])
    memory_snippets = _keyword_search(query_text, [(f.fact_text, f.fact_text) for f in facts])

    return BusinessContext(
        system_prompt=business.system_prompt or "You are a helpful assistant.",
        knowledge_snippets=knowledge_snippets,
        memory_snippets=memory_snippets,
    )


def _keyword_search(query_text: str, items: list[tuple[str, str]]) -> list[str]:
    """
    items = [(content, label), ...]. Returns content of items that
    share at least one word with the query. Naive but transparent —
    good enough until real usage proves it's not (Rule 5).
    """
    query_words = set(query_text.lower().split())
    matches = []
    for content, _label in items:
        content_words = set(content.lower().split())
        if query_words & content_words:
            matches.append(content)
    return matches
