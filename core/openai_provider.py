"""
OpenAI implementation of LLMProvider.
Uses the official openai SDK — never calls the HTTP API directly.
Only supports chat-completion models (gpt-4o-mini by default).
"""
from openai import OpenAI

from core.llm_provider import LLMProvider, LLMResponse


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self._client = OpenAI(api_key=api_key)
        self._model = model

    def complete(self, system_prompt: str, messages: list[dict]) -> LLMResponse:
        """
        Prepends a system message then passes user/assistant history
        to the OpenAI chat completions endpoint.
        tool_call is None for now — tool support added when needed.
        """
        openai_messages = [{"role": "system", "content": system_prompt}] + messages
        response = self._client.chat.completions.create(
            model=self._model,
            messages=openai_messages,
        )
        reply_text = response.choices[0].message.content or ""
        return LLMResponse(reply_text=reply_text, tool_call=None)
