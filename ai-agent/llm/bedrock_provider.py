"""
AWS Bedrock LLM provider — connects to AWS Bedrock to run Claude 3 Haiku.
"""

import os
import re
import json
import logging
import asyncio
import boto3

from llm.base import BaseLLM

logger = logging.getLogger(__name__)


class BedrockProvider(BaseLLM):
    """LLM provider using AWS Bedrock with Claude Haiku."""

    def __init__(
        self,
        model_id: str | None = None,
        region: str | None = None,
    ):
        # Allow override from arguments or environment variables
        self.model_id = model_id or os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
        self.region = region or os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1"
        
        aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        
        # Create bedrock client
        client_kwargs = {
            "service_name": "bedrock-runtime",
            "region_name": self.region
        }
        if aws_access_key and aws_secret_key:
            client_kwargs["aws_access_key_id"] = aws_access_key
            client_kwargs["aws_secret_access_key"] = aws_secret_key
            
        logger.info("Initializing BedrockProvider with model_id=%s, region=%s", self.model_id, self.region)
        self.client = boto3.client(**client_kwargs)
        self.last_usage = {"input_tokens": 0, "output_tokens": 0}


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
        # Separate system message if present
        bedrock_messages = []
        extracted_system = system

        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")
            if role == "system":
                if not extracted_system:
                    extracted_system = content
            else:
                # Standard Bedrock message structure
                bedrock_messages.append({
                    "role": role,
                    "content": content
                })

        # Build payload
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": num_predict,
            "temperature": temperature,
            "messages": bedrock_messages
        }
        if extracted_system:
            payload["system"] = extracted_system

        try:
            # invoke_model is a synchronous blocking call. Run in an executor to keep async loop responsive.
            loop = asyncio.get_event_loop()
            
            def _invoke():
                return self.client.invoke_model(
                    body=json.dumps(payload),
                    modelId=self.model_id,
                    contentType="application/json",
                    accept="application/json"
                )
                
            response = await loop.run_in_executor(None, _invoke)
            response_body = json.loads(response.get("body").read())
            
            # Extract and update token usage metrics
            usage = response_body.get("usage")
            if usage:
                input_t = usage.get("input_tokens", 0)
                output_t = usage.get("output_tokens", 0)
                logger.info(f"Bedrock Token Usage: Input: {input_t} tokens, Output: {output_t} tokens, Total: {input_t + output_t} tokens")
                self.last_usage["input_tokens"] += input_t
                self.last_usage["output_tokens"] += output_t
            
            # Extract content from Claude response
            content_list = response_body.get("content", [])
            content = ""
            if content_list and isinstance(content_list, list):
                content = content_list[0].get("text", "")
            elif isinstance(content_list, str):
                content = content_list
            return content.strip()

        except Exception as e:
            logger.error("Bedrock generation failed: %s", str(e))
            raise RuntimeError(f"LLM generation failed: {str(e)}") from e

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

    def get_and_reset_usage(self) -> dict:
        """Retrieve and reset the token usage metrics from recent operations."""
        usage = self.last_usage.copy()
        self.last_usage = {"input_tokens": 0, "output_tokens": 0}
        return usage

