"""
Pydantic schemas — single shared source of truth between api/
and cli/ (Rule 7). Never redefine these shapes separately in
either place.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel


class BusinessCreate(BaseModel):
    name: str


class BusinessRead(BaseModel):
    id: uuid.UUID
    developer_id: uuid.UUID
    name: str
    status: str
    admin_channel: str | None
    llm_provider: str | None
    system_prompt: str | None
    created_at: datetime

    class Config:
        from_attributes = True  # allows BusinessRead.model_validate(sqlalchemy_object)


class BusinessKeysSet(BaseModel):
    provider: str
    api_key: str


class BusinessPublish(BaseModel):
    system_prompt: str


class KnowledgeDocCreate(BaseModel):
    filename: str
    content: str


class BusinessPublish(BaseModel):
    system_prompt: str


class KnowledgeDocCreate(BaseModel):
    filename: str
    content: str


class MemoryFactCreate(BaseModel):
    fact_text: str


class BusinessChannelsSet(BaseModel):
    whatsapp_phone_number_id: str
