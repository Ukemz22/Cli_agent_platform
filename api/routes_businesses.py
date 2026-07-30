"""
Business management routes. Every route here requires a valid
developer token (Chapter 2) and enforces tenant ownership.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.db import get_db
from core.models import Developer, Business, KnowledgeDoc, MemoryFact, KnowledgeDoc
from core.crypto import encrypt_key
from core.schemas import BusinessCreate, BusinessRead, BusinessKeysSet, BusinessPublish, KnowledgeDocCreate, MemoryFactCreate, BusinessPublish, KnowledgeDocCreate
from api.deps import get_current_developer, get_owned_business

router = APIRouter(prefix="/businesses", tags=["businesses"])


@router.post("", response_model=BusinessRead)
def create_business(
    payload: BusinessCreate,
    developer: Developer = Depends(get_current_developer),
    db: Session = Depends(get_db),
):
    business = Business(developer_id=developer.id, name=payload.name)
    db.add(business)
    db.commit()
    db.refresh(business)
    return business


@router.get("/{business_id}", response_model=BusinessRead)
def get_business(
    business: Business = Depends(get_owned_business),
):
    return business


@router.patch("/{business_id}/keys", response_model=BusinessRead)
def set_business_keys(
    payload: BusinessKeysSet,
    business: Business = Depends(get_owned_business),
    db: Session = Depends(get_db),
):
    business.llm_provider = payload.provider
    business.llm_api_key_encrypted = encrypt_key(payload.api_key)
    db.add(business)
    db.commit()
    db.refresh(business)
    return business


@router.patch("/{business_id}/publish", response_model=BusinessRead)
def publish_business(
    payload: BusinessPublish,
    business: Business = Depends(get_owned_business),
    db: Session = Depends(get_db),
):
    business.system_prompt = payload.system_prompt
    business.status = "live"
    db.add(business)
    db.commit()
    db.refresh(business)
    return business


@router.post("/{business_id}/knowledge")
def add_knowledge_doc(
    payload: KnowledgeDocCreate,
    business: Business = Depends(get_owned_business),
    db: Session = Depends(get_db),
):
    existing = db.query(KnowledgeDoc).filter(
        KnowledgeDoc.business_id == business.id,
        KnowledgeDoc.filename == payload.filename,
    ).first()

    if existing:
        existing.content = payload.content
    else:
        existing = KnowledgeDoc(business_id=business.id, filename=payload.filename, content=payload.content)
        db.add(existing)

    db.commit()
    return {"status": "synced", "filename": payload.filename}


@router.patch("/{business_id}/publish", response_model=BusinessRead)
def publish_business(
    payload: BusinessPublish,
    business: Business = Depends(get_owned_business),
    db: Session = Depends(get_db),
):
    business.system_prompt = payload.system_prompt
    business.status = "live"
    db.add(business)
    db.commit()
    db.refresh(business)
    return business


@router.post("/{business_id}/knowledge")
def add_knowledge_doc(
    payload: KnowledgeDocCreate,
    business: Business = Depends(get_owned_business),
    db: Session = Depends(get_db),
):
    existing = db.query(KnowledgeDoc).filter(
        KnowledgeDoc.business_id == business.id,
        KnowledgeDoc.filename == payload.filename,
    ).first()

    if existing:
        existing.content = payload.content
    else:
        existing = KnowledgeDoc(business_id=business.id, filename=payload.filename, content=payload.content)
        db.add(existing)

    db.commit()
    return {"status": "synced", "filename": payload.filename}


@router.post("/{business_id}/memory")
def add_memory_fact(
    payload: MemoryFactCreate,
    business: Business = Depends(get_owned_business),
    db: Session = Depends(get_db),
):
    fact = MemoryFact(business_id=business.id, fact_text=payload.fact_text, source="cli_correction")
    db.add(fact)
    db.commit()
    return {"status": "saved"}
