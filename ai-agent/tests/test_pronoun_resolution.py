import os
import sys
import asyncio
from pathlib import Path

agent_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(agent_dir))
os.chdir(agent_dir)

from dotenv import load_dotenv
load_dotenv()

active_token = "7570|AZYlXTfTUN3o6r1CjX0PvJErefbRrS7oKnw1TRbg"
from app import _create_llm, agent
from agent.memory import memory_manager

async def run_query(message: str, session_id: str):
    print(f"\n==========================================")
    print(f"QUERY: '{message}'")
    print(f"==========================================")
    
    memory = memory_manager.get_session(session_id)
    resolved_message = memory.resolve_pronoun(message)
    print(f"Resolved Message: '{resolved_message}'")
    context = memory.get_context()
    print(f"Context: {context}")
    
    response_text, metadata = await agent.run(
        message=resolved_message,
        context=context,
        billerq_token=active_token,
        billerq_api_url="https://customerapi.billerq.com/api"
    )
    
    if metadata.get("customer_id") and metadata.get("customer_name"):
        memory.update_customer(metadata["customer_id"], metadata["customer_name"])
    memory.update_intent(metadata.get("intent", "UNKNOWN"))
    memory.add_turn(message, response_text)
    
    print("\nRESPONSE:\n")
    print(response_text)
    print(f"\nMetadata: {metadata}")

async def main():
    session_id = "test-pronouns"
    await run_query("details of Jinto Joseph", session_id)
    await run_query("what is his phone number", session_id)

if __name__ == "__main__":
    asyncio.run(main())
