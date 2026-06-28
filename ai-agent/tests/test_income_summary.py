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
from tools.reports import get_income_summary
from api.client import api_client

async def main():
    api_client._request_token_override = active_token
    api_client.base_url = "https://customer.billerq.com/public/api"
    
    result = await get_income_summary(month="May", year="2026")
    print("INCOME SUMMARY for May 2026:")
    import json
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
