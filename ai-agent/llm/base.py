"""
Abstract base class for LLM providers.

Swap between Ollama (Qwen3) and AWS Bedrock (Claude Haiku)
by changing the provider — no other code changes needed.
"""

from abc import ABC, abstractmethod


class BaseLLM(ABC):
    """Abstract LLM provider interface."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.3,
    ) -> str:
        """Generate a text response from the LLM.

        Args:
            prompt: The user/input prompt.
            system: System-level instruction prompt.
            temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative).

        Returns:
            The generated text response.
        """
        ...

    @abstractmethod
    async def generate_json(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.1,
    ) -> dict:
        """Generate a structured JSON response from the LLM.

        Args:
            prompt: The user/input prompt.
            system: System-level instruction prompt.
            temperature: Low temperature for consistent structured output.

        Returns:
            Parsed dictionary from the LLM's JSON output.
        """
        ...
