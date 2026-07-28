"""
Business management routes. Every route here requires a valid
developer token (Chapter 2) and enforces tenant ownership.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.db import get_db
from core.models import Developer, Business
from core.crypto import encrypt_key
from core.schemas import BusinessCreate, BusinessRead, BusinessKeysSet
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
