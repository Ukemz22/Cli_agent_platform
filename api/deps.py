"""
Shared FastAPI dependencies. get_current_developer is used on
every protected route from here on — this is the single place
that turns 'a token in a header' into 'a real Developer row'.
"""
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from core.db import get_db
from core.models import Developer
from core.security import hash_token


def get_current_developer(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Developer:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or malformed token")

    raw_token = authorization.removeprefix("Bearer ").strip()
    token_hash = hash_token(raw_token)

    developer = db.query(Developer).filter(Developer.token_hash == token_hash).first()
    if developer is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    if developer.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Developer account not active")

    return developer


def get_owned_business(business_id: str, developer: Developer = Depends(get_current_developer), db: Session = Depends(get_db)):
    """
    Confirms the current developer owns the business referenced
    in the URL. Raises 404 (not 403) if it belongs to someone
    else — we don't reveal that the business even exists.
    """
    from core.models import Business

    business = db.query(Business).filter(
        Business.id == business_id,
        Business.developer_id == developer.id,
    ).first()

    if business is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")

    return business
