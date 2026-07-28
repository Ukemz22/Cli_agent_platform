"""
Business management routes. Every route here requires a valid
developer token (Chapter 2) and enforces tenant ownership.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.db import get_db
from core.models import Developer, Business
from core.schemas import BusinessCreate, BusinessRead
from api.deps import get_current_developer

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
