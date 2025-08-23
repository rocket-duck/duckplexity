import os
import httpx

API_URL = "https://api.perplexity.ai/chat/completions"

async def query(prompt: str, api_key: str | None = None) -> str:
    """Send prompt to Perplexity API and return the response text."""
    api_key = api_key or os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        raise RuntimeError("PERPLEXITY_API_KEY is not set")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "llama-3.1-sonar-small-128k-online",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 512,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
