import os
import sys
import asyncio
from pathlib import Path

agent_dir = Path("c:/Users/Lenovo/Desktop/Chatbot/ai-agent")
sys.path.insert(0, str(agent_dir))
os.chdir(agent_dir)

from dotenv import load_dotenv
load_dotenv()

active_token = "7570|AZYlXTfTUN3o6r1CjX0PvJErefbRrS7oKnw1TRbg"
from app import agent

async def run_query(message: str):
    print(f"\n==========================================")
    print(f"QUERY: '{message}'")
    print(f"==========================================")
    
    response_text, metadata = await agent.run(
        message=message,
        context={},
        billerq_token=active_token,
        billerq_api_url="https://customerapi.billerq.com/api"
    )
    
    print("\nRESPONSE:\n")
    print(response_text)
    print(f"\nMetadata: {metadata}")

async def run_query_with_context(message: str, context: dict):
    print(f"\n==========================================")
    print(f"QUERY: '{message}'")
    print(f"Context: {context}")
    print(f"==========================================")
    
    response_text, metadata = await agent.run(
        message=message,
        context=context,
        billerq_token=active_token,
        billerq_api_url="https://customerapi.billerq.com/api"
    )
    
    print("\nRESPONSE:\n")
    print(response_text)
    print(f"\nMetadata: {metadata}")

async def main():
    # Test 1: Full details first to set context
    print("\n=== TEST 1: Full details ===")
    await run_query("show me the details of jinto joseph")
    
    context = {
        "last_customer_id": 44357,
        "last_customer_name": "Jinto Joseph",
        "last_intent": "UNKNOWN",
        "history": [{"user": "show me the details of jinto joseph", "assistant": "Customer Profile: ..."}]
    }

    # Test 2: Multi-field - phone number and customer id
    print("\n=== TEST 2: Multi-field phone number AND customer id ===")
    await run_query_with_context("his phone number and customer id", context)

    # Test 3: Multi-field - subscriber id and phone number  
    print("\n=== TEST 3: Multi-field subscriber id AND phone number ===")
    await run_query_with_context("his subscriber id and phone number", context)

    # Test 4: Single field - just phone number
    print("\n=== TEST 4: Single field phone number ===")
    await run_query_with_context("his phone number", context)

    # Test 5: Single field - just place
    print("\n=== TEST 5: Single field place ===")
    await run_query("place of jinto joseph")

if __name__ == "__main__":
    asyncio.run(main())
