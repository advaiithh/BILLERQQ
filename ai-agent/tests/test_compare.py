import os, sys, asyncio
from pathlib import Path

agent_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(agent_dir))
os.chdir(agent_dir)

from dotenv import load_dotenv
load_dotenv()

from app import agent

active_token = "7570|AZYlXTfTUN3o6r1CjX0PvJErefbRrS7oKnw1TRbg"

async def main():
    print("\n=== TEST: compare jinto and advaith ===")
    resp, meta = await agent.run(
        message="compare jinto and advaith",
        context={},
        billerq_token=active_token,
        billerq_api_url="https://customerapi.billerq.com/api"
    )
    print(resp)
    print("Meta:", meta)

if __name__ == "__main__":
    asyncio.run(main())
