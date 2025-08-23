import os
import logging
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
        # Use a generally available model to avoid 400 errors
        "model": "sonar",
        "messages": [{"role": "user", "content": prompt}]
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(API_URL, headers=headers, json=payload)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            # Surface API error details for easier debugging
            raise RuntimeError(f"Perplexity API error: {response.text}") from exc
        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()
        logging.info("Perplexity response: %s", content)
        return content
