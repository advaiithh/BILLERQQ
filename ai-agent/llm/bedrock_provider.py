"""
AWS Bedrock LLM provider — Claude Haiku via boto3 Bedrock Runtime.

Requires env vars:
    AWS_ACCESS_KEY_ID
    AWS_SECRET_ACCESS_KEY
    AWS_REGION          (default: us-east-1)
    BEDROCK_MODEL_ID    (default: anthropic.claude-3-haiku-20240307-v1:0)
"""

import json
import re
import logging
import asyncio

from llm.base import BaseLLM

logger = logging.getLogger(__name__)


class BedrockProvider(BaseLLM):
    """LLM provider using AWS Bedrock with Claude Haiku (or Claude Sonnet 4.5)."""

    def __init__(
        self,
        model_id: str = "anthropic.claude-3-haiku-20240307-v1:0",
        region: str = "us-east-1",
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        aws_session_token: str | None = None,
    ):
        import boto3

        self.model_id = model_id
        self.region = region

        # Create the bedrock-runtime client
        kwargs = {"region_name": region}
        if aws_access_key_id:
            kwargs["aws_access_key_id"] = aws_access_key_id
        if aws_secret_access_key:
            kwargs["aws_secret_access_key"] = aws_secret_access_key
        if aws_session_token:
            kwargs["aws_session_token"] = aws_session_token

        self._client = boto3.client("bedrock-runtime", **kwargs)
        logger.info(
            "BedrockProvider initialized: model=%s, region=%s",
            model_id,
            region,
        )

    def _invoke_sync(self, body: dict) -> str:
        """Invoke the Bedrock model synchronously (runs in thread pool)."""
        response = self._client.invoke_model(
            modelId=self.model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body),
        )
        response_body = json.loads(response["body"].read())

        # Claude Bedrock response structure
        content_blocks = response_body.get("content", [])
        text_parts = [
            block["text"]
            for block in content_blocks
            if block.get("type") == "text"
        ]
        return "".join(text_parts).strip()

    async def generate(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.3,
    ) -> str:
        """Generate a text response using Bedrock Claude."""
        body: dict = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1024,
            "temperature": temperature,
            "messages": [
                {"role": "user", "content": prompt},
            ],
        }
        if system:
            body["system"] = system

        try:
            # boto3 is synchronous — run in a thread pool to keep FastAPI async
            loop = asyncio.get_event_loop()
            text = await loop.run_in_executor(None, self._invoke_sync, body)
            logger.debug("Bedrock response length: %d chars", len(text))
            return text
        except Exception as e:
            logger.error("Bedrock generation failed: %s", str(e))
            raise RuntimeError(f"Bedrock LLM generation failed: {str(e)}") from e

    async def generate_json(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.1,
    ) -> dict:
        """Generate a structured JSON response via Bedrock Claude."""
        # Append JSON instruction to system prompt
        json_system = (system + "\n\n" if system else "") + (
            "You MUST respond with valid JSON only. No explanation, no markdown fences."
        )
        raw = await self.generate(prompt, system=json_system, temperature=temperature)

        # Try direct parse
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code fences
        json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", raw, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Try finding any JSON object
        brace_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        logger.error("Failed to parse JSON from Bedrock response: %s", raw[:300])
        return {"error": "Failed to parse structured response", "raw": raw}

    async def chat(
        self,
        messages: list,
        temperature: float = 0.3,
    ) -> str:
        """Multi-turn chat via Bedrock Claude.

        Args:
            messages: List of {"role": "user"|"assistant"|"system", "content": "..."}
        """
        # Separate system messages from conversation
        system_parts = [m["content"] for m in messages if m["role"] == "system"]
        conv = [m for m in messages if m["role"] != "system"]

        body: dict = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1024,
            "temperature": temperature,
            "messages": conv,
        }
        if system_parts:
            body["system"] = "\n\n".join(system_parts)

        try:
            loop = asyncio.get_event_loop()
            text = await loop.run_in_executor(None, self._invoke_sync, body)
            logger.debug("Bedrock chat response length: %d chars", len(text))
            return text
        except Exception as e:
            logger.error("Bedrock chat failed: %s", str(e))
            raise RuntimeError(f"Bedrock LLM chat failed: {str(e)}") from e

    async def chat_json(
        self,
        messages: list,
        temperature: float = 0.1,
    ) -> dict:
        """Multi-turn chat that returns structured JSON."""
        raw = await self.chat(messages, temperature=temperature)

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", raw, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        brace_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        logger.error("Failed to parse JSON from Bedrock chat: %s", raw[:300])
        return {"error": "Failed to parse structured response", "raw": raw}
