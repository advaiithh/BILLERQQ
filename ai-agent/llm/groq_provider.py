"""
Groq Cloud LLM provider — connects to Groq API using Llama 3.3.
"""

import os
import re
import json
import logging
import httpx

from llm.base import BaseLLM

logger = logging.getLogger(__name__)


class GroqProvider(BaseLLM):
    """LLM provider using Groq API with Llama 3.3."""

    def __init__(
        self,
        model_id: str | None = None,
        api_key: str | None = None,
    ):
        self.model_id = model_id or os.getenv("GROQ_MODEL_ID", "llama-3.3-70b-versatile")
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
        
        if not self.api_key:
            logger.warning("GROQ_API_KEY is not set. Requests to Groq will fail.")
        else:
            logger.info("Initializing GroqProvider with model_id=%s", self.model_id)

    async def generate(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.3,
        num_predict: int = 400,
    ) -> str:
        """Generate a text response from the LLM.

        Args:
            prompt: The user/input prompt.
            system: System-level instruction prompt.
            temperature: Sampling temperature.
            num_predict: Max tokens to predict/generate.

        Returns:
            The generated text response.
        """
        messages = [
            {"role": "user", "content": prompt}
        ]
        return await self.chat(messages, temperature, num_predict, system)

    async def generate_json(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.1,
        num_predict: int = 400,
    ) -> dict:
        """Generate a structured JSON response from the LLM."""
        raw = await self.generate(prompt, system, temperature, num_predict)
        return self._parse_json(raw)

    async def chat(
        self,
        messages: list,
        temperature: float = 0.3,
        num_predict: int = 400,
        system: str = "",
    ) -> str:
        """Generate a chat response using a list of messages.

        Args:
            messages: List of message dictionaries, e.g. [{"role": "user", "content": "..."}]
            temperature: Sampling temperature.
            num_predict: Maximum number of tokens to predict/generate.
            system: Optional system prompt to override.

        Returns:
            The generated text response.
        """
        formatted_messages = []
        
        # If system argument is explicitly provided, add it first.
        # Otherwise, if "system" exists in messages, it will be added as part of the loop.
        if system:
            formatted_messages.append({"role": "system", "content": system})

        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")
            formatted_messages.append({"role": role, "content": content})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": self.model_id,
            "messages": formatted_messages,
            "temperature": temperature,
            "max_tokens": num_predict,
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(self.base_url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                return content.strip()
        except Exception as e:
            logger.error("Groq generation failed: %s", str(e))
            raise RuntimeError(f"Groq LLM generation failed: {str(e)}") from e

    async def chat_json(
        self,
        messages: list,
        temperature: float = 0.1,
        num_predict: int = 400,
        system: str = "",
    ) -> dict:
        """Generate a structured JSON response from a chat session.

        Extracts JSON from the response.
        """
        raw = await self.chat(messages, temperature, num_predict, system)
        return self._parse_json(raw)

    def _parse_json(self, raw: str) -> dict:
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
