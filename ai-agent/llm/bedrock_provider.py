"""
AWS Bedrock LLM provider stub — Phase 5 implementation.

Will use Claude Haiku via AWS Bedrock when ready.
"""

import logging

from llm.base import BaseLLM

logger = logging.getLogger(__name__)


class BedrockProvider(BaseLLM):
    """LLM provider using AWS Bedrock with Claude Haiku.

    Placeholder for Phase 5 — currently raises NotImplementedError.

    Future implementation will require:
        - AWS credentials (access key, secret key, region)
        - boto3 bedrock-runtime client
        - Claude Haiku model ID
    """

    def __init__(
        self,
        model_id: str = "anthropic.claude-3-haiku-20240307-v1:0",
        region: str = "us-east-1",
    ):
        self.model_id = model_id
        self.region = region
        logger.info("BedrockProvider initialized (stub — not yet functional)")

    async def generate(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.3,
    ) -> str:
        """Generate text via Bedrock — not yet implemented."""
        raise NotImplementedError(
            "Bedrock provider is planned for Phase 5. "
            "Switch LLM_PROVIDER to 'ollama' in your .env file."
        )

    async def generate_json(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.1,
    ) -> dict:
        """Generate JSON via Bedrock — not yet implemented."""
        raise NotImplementedError(
            "Bedrock provider is planned for Phase 5. "
            "Switch LLM_PROVIDER to 'ollama' in your .env file."
        )
