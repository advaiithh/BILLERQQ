"""
Ollama LLM provider — connects to local Ollama server running Qwen3.
"""

import json
import re
import logging
import ollama as ollama_client

from llm.base import BaseLLM

logger = logging.getLogger(__name__)


class OllamaProvider(BaseLLM):
    """LLM provider using Ollama with Qwen3 (or any local model)."""

    def __init__(self, model: str = "qwen3", host: str = "http://localhost:11434"):
        self.model = model
        self.host = host
        self.client = ollama_client.AsyncClient(host=host)

    async def generate(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.3,
        num_predict: int = 400,
    ) -> str:
        """Generate a text response using Ollama."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            response = await self.client.chat(
                model=self.model,
                messages=messages,
                options={"temperature": temperature, "num_predict": num_predict},
            )
            content = response["message"]["content"]

            # Qwen3 uses <think>...</think> blocks for chain-of-thought.
            # Strip them out — we only want the final answer.
            content = re.sub(
                r"<think>.*?</think>",
                "",
                content,
                flags=re.DOTALL,
            ).strip()

            logger.debug("Ollama response length: %d chars", len(content))
            return content

        except Exception as e:
            logger.error("Ollama generation failed: %s", str(e))
            raise RuntimeError(f"LLM generation failed: {str(e)}") from e

    async def generate_json(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.1,
        num_predict: int = 400,
    ) -> dict:
        """Generate a structured JSON response using Ollama.

        Extracts JSON from the response even if the model wraps it
        in markdown code fences or extra text.
        """
        raw = await self.generate(prompt, system, temperature, num_predict)

        # Try direct parse first
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code fences: ```json ... ``` or ``` ... ```
        json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", raw, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Try finding any JSON object in the response
        brace_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        logger.error("Failed to parse JSON from LLM response: %s", raw[:200])
        return {"error": "Failed to parse structured response", "raw": raw}

    async def chat(
        self,
        messages: list,
        temperature: float = 0.3,
        num_predict: int = 400,
    ) -> str:
        """Generate a chat response using a list of messages.

        Args:
            messages: List of message dictionaries, e.g. [{"role": "user", "content": "..."}]
            temperature: Sampling temperature.
            num_predict: Maximum number of tokens to predict/generate.

        Returns:
            The generated text response.
        """
        try:
            response = await self.client.chat(
                model=self.model,
                messages=messages,
                options={"temperature": temperature, "num_predict": num_predict},
            )
            content = response["message"]["content"]

            # Clean any leftover think tags (unlikely for Mistral but keeps it safe)
            content = re.sub(
                r"<think>.*?</think>",
                "",
                content,
                flags=re.DOTALL,
            ).strip()

            logger.debug("Ollama chat response length: %d chars", len(content))
            return content

        except Exception as e:
            logger.error("Ollama chat failed: %s", str(e))
            raise RuntimeError(f"LLM chat failed: {str(e)}") from e

    async def chat_json(
        self,
        messages: list,
        temperature: float = 0.1,
        num_predict: int = 400,
    ) -> dict:
        """Generate a structured JSON response from a chat session.

        Extracts JSON from the response.
        """
        raw = await self.chat(messages, temperature, num_predict)

        # Try direct parse first
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code fences: ```json ... ``` or ``` ... ```
        json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", raw, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Try finding any JSON object in the response
        brace_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        logger.error("Failed to parse JSON from LLM chat response: %s", raw[:200])
        return {"error": "Failed to parse structured response", "raw": raw}

