"""Quick test to replicate exactly how BillerQClient makes requests."""
import asyncio
import httpx

async def run_test():
    from api.client import BillerQClient
    client = BillerQClient()
    
    # Run client login
    print("Logging in via BillerQClient...")
    await client._ensure_token()
    
    print(f"Logged in successfully!")
    print(f"Resolved base_url: {client.base_url}")
    print(f"Token: {client._token[:25]}...")
    
    # Request get_recurring_data
    try:
        response = await client._request_with_retry("GET", "/admin/get-recurring-data")
        print("\nSuccessfully fetched get_recurring_data!")
        print(f"Keys in response: {list(response.keys()) if isinstance(response, dict) else type(response)}")
        print(f"Data preview: {str(response)[:1000]}")
    except Exception as e:
        print(f"\nFailed to fetch get_recurring_data: {e}")

if __name__ == "__main__":
    asyncio.run(run_test())
