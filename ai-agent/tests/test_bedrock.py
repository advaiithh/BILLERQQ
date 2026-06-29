"""
Quick test — run this AFTER adding your real AWS keys to .env.
Usage:  python ai-agent/tests/test_bedrock.py
"""
import asyncio
import os
import sys

sys.path.insert(0, "ai-agent")

from dotenv import load_dotenv
load_dotenv("ai-agent/.env")

async def main():
    key    = os.getenv("AWS_ACCESS_KEY_ID", "")
    secret = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    region = os.getenv("AWS_REGION", "eu-north-1")
    model  = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-haiku-4-5-20251001-v1:0")

    if "REPLACE" in key or not key:
        print("❌  You haven't added your AWS credentials to .env yet.")
        print("    Follow the steps below to get them.\n")
        print("Steps to get AWS credentials:")
        print("  1. Open https://364046407111.signin.aws.amazon.com/console")
        print("  2. Log in as  billerqai")
        print("  3. Top-right corner → click your name → 'Security credentials'")
        print("  4. Scroll to 'Access keys' → click 'Create access key'")
        print("  5. Choose 'Application running outside AWS' → Next → Create")
        print("  6. COPY the Access Key ID and Secret Access Key NOW (shown once)")
        print("  7. Paste them into ai-agent/.env")
        print("     AWS_ACCESS_KEY_ID=AKIA...")
        print("     AWS_SECRET_ACCESS_KEY=...")
        print("  8. Run this script again: python ai-agent/tests/test_bedrock.py")
        return

    print(f"✅  Credentials found.")
    print(f"    Region : {region}")
    print(f"    Model  : {model}")
    print(f"    Key ID : {key[:8]}...")
    print("\n⏳  Calling Claude Haiku 4.5 on Bedrock...\n")

    from llm.bedrock_provider import BedrockProvider
    provider = BedrockProvider(
        model_id=model,
        region=region,
        aws_access_key_id=key,
        aws_secret_access_key=secret,
    )

    try:
        response = await provider.generate(
            prompt="Say 'Hello! Claude Haiku is working on BillerQ!' in exactly those words.",
            system="You are a helpful AI assistant for BillerQ.",
        )
        print("🎉  Claude says:")
        print("   ", response)
        print("\n✅  Bedrock integration is working! Restart the backend to use it.")
    except Exception as e:
        print(f"❌  Error calling Bedrock: {e}")
        if "ExpiredTokenException" in str(e) or "Signature" in str(e):
            print("\n   → Fix: Sync your Windows clock:")
            print("      Settings → Time & Language → Date & Time → Sync now")
        elif "AccessDeniedException" in str(e) or "UnauthorizedClientException" in str(e):
            print("\n   → Fix: The IAM user needs 'bedrock:InvokeModel' permission.")
            print("      Ask your AWS admin to attach the policy 'AmazonBedrockFullAccess' to billerqai.")
        elif "ResourceNotFoundException" in str(e):
            print(f"\n   → Fix: Model '{model}' is not enabled in region '{region}'.")
            print("      Go to AWS Bedrock → Model access → Enable Claude Haiku 4.5")

asyncio.run(main())
