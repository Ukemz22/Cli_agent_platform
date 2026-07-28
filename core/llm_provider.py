"""
Swappable LLM provider interface. Agent Runtime (Chapter 3) only
ever talks to this interface — never to a specific provider's SDK
directly. Real providers (OpenAI, Anthropic, etc) get added when
we actually wire a live BYOK key; for now, tests use FakeLLMProvider.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class LLMResponse:
    reply_text: str
    tool_call: dict | None = None


class LLMProvider(ABC):
    @abstractmethod
    def complete(self, system_prompt: str, messages: list[dict]) -> LLMResponse:
        """messages = [{'role': 'user'|'assistant', 'content': str}, ...]"""
        raise NotImplementedError


class FakeLLMProvider(LLMProvider):
    """
    Test double. Configure it with a canned response, or a queue of
    responses for multi-turn tests (e.g. tool_call then final reply).
    """
    def __init__(self, responses: list[LLMResponse] = field(default_factory=list)):
        self._responses = list(responses)
        self.calls: list[dict] = []  # records every call, for assertions in tests

    def complete(self, system_prompt: str, messages: list[dict]) -> LLMResponse:
        self.calls.append({"system_prompt": system_prompt, "messages": messages})
        if not self._responses:
            return LLMResponse(reply_text="(no canned response configured)")
        return self._responses.pop(0)
