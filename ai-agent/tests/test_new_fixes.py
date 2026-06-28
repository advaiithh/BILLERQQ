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

async def run_query(message: str, context: dict):
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
    return metadata

async def main():
    # 1. Query for Jinto Joseph details
    meta1 = await run_query("show me the details of jinto", {})
    
    # Context after details query
    context = {
        "last_customer_id": meta1.get("customer_id"),
        "last_customer_name": meta1.get("customer_name"),
        "history": []
    }
    
    # 2. Query for "his phone number and customer id"
    # Note: "his" resolves to "Jinto Joseph's"
    await run_query("Jinto Joseph's phone number and customer id", context)
    
    # 3. Query for "customer id"
    await run_query("customer id", context)
    
    # 4. Query for "his subscriber id and phone number"
    # Note: "his" resolves to "Jinto Joseph's"
    await run_query("Jinto Joseph's subscriber id and phone number", context)

if __name__ == "__main__":
    asyncio.run(main())
