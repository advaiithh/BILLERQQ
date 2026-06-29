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
from api.client import api_client

async def main():
    api_client._request_token_override = active_token
    api_client.base_url = "https://customerapi.billerq.com/api"
    
    import json

    # 1. Fetch get_customer_payment_report
    try:
        res1 = await api_client.get("get_customer_payment_report")
        print("\n=== get_customer_payment_report ===")
        print(f"Type of res1: {type(res1)}")
        if isinstance(res1, dict):
            print(f"Keys: {res1.keys()}")
            payment_field = res1.get("payment", {})
            print(f"Type of payment field: {type(payment_field)}")
            if isinstance(payment_field, dict):
                print(f"payment Keys: {payment_field.keys()}")
                print(f"payment List length: {len(payment_field.get('data', []))}")
                if payment_field.get('data'):
                    print("Sample payment record:")
                    print(json.dumps(payment_field.get('data')[0], indent=2))
            elif isinstance(payment_field, list):
                print(f"payment list length: {len(payment_field)}")
                if payment_field:
                    print("Sample payment record:")
                    print(json.dumps(payment_field[0], indent=2))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
