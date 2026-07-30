"""
Factory: turns a Business row into a live LLMProvider instance.
Decrypts the stored API key and instantiates the right provider.
Add new elif branches here when supporting Anthropic, Google, etc.
"""
from fastapi import HTTPException, status

from core.crypto import decrypt_key
from core.llm_provider import LLMProvider
from core.models import Business


def get_llm_for_business(business: Business) -> LLMProvider:
    if not business.llm_provider:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Business has no LLM provider set. Run: agent keys-set --provider openai --key <KEY>",
        )
    if not business.llm_api_key_encrypted:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Business has no LLM API key stored.",
        )

    raw_key = decrypt_key(business.llm_api_key_encrypted)

    if business.llm_provider == "openai":
        from core.openai_provider import OpenAIProvider
        return OpenAIProvider(api_key=raw_key)

    if business.llm_provider == "groq":
        from core.groq_provider import GroqProvider
        return GroqProvider(api_key=raw_key)

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"Unsupported LLM provider: {business.llm_provider!r}",
    )
