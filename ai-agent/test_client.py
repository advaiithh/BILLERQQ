"""Quick test to replicate exactly how BillerQClient makes requests."""
import asyncio
import httpx

async def test():
    base_url = "https://customerapi.billerq.com"
    token = "23765|VsM9pM9QBnh48eE2ygpNjZj6Cw6dtlcdoUXO7pOM"
    prefix = "api"

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }

    # This is how client.py builds the endpoint
    endpoint = "/admin/show-customer"  # from registry
    clean_endpoint = endpoint.lstrip("/")
    req_endpoint = f"/{prefix}/{clean_endpoint}"  # -> /api/admin/show-customer

    print(f"base_url: {base_url}")
    print(f"req_endpoint: {req_endpoint}")
    print(f"Full URL will be: {base_url}{req_endpoint}")
    print(f"Token (first 20): {token[:20]}...")

    async with httpx.AsyncClient(
        base_url=base_url,
        headers=headers,
        timeout=httpx.Timeout(30.0),
        follow_redirects=True,
    ) as client:
        r = await client.get(req_endpoint, params={"page": 1, "page_length": 5})
        print(f"\nStatus: {r.status_code}")
        print(f"URL used: {r.url}")
        print(f"Response: {r.text[:500]}")

asyncio.run(test())
