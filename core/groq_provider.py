"""
Groq implementation of LLMProvider — for testing without a funded OpenAI key.
The Groq SDK mirrors the OpenAI SDK interface exactly.
Default model: llama-3.3-70b-versatile (fast, free-tier friendly).
Remove this file when switching to a production LLM provider.
"""
from groq import Groq

from core.llm_provider import LLMProvider, LLMResponse


class GroqProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        self._client = Groq(api_key=api_key)
        self._model = model

    def complete(self, system_prompt: str, messages: list[dict]) -> LLMResponse:
        """
        Prepends a system message then passes user/assistant history
        to the Groq chat completions endpoint.
        """
        groq_messages = [{"role": "system", "content": system_prompt}] + messages
        response = self._client.chat.completions.create(
            model=self._model,
            messages=groq_messages,
        )
        reply_text = response.choices[0].message.content or ""
        return LLMResponse(reply_text=reply_text, tool_call=None)
