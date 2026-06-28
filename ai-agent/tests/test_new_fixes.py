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

async def main():
    await run_query("show the place of Jinto Joseph")
    await run_query("give me the details about the payments collected by archana u m")
    await run_query("customers who have high payment due")

if __name__ == "__main__":
    asyncio.run(main())
