import os
import re
from typing import Any, Dict

import httpx

API_URL = "https://api.perplexity.ai/chat/completions"

async def query(prompt: str, api_key: str | None = None) -> Dict[str, Any]:
    """Send prompt to the Perplexity API and return the full response payload."""
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
        data: Dict[str, Any] = response.json()
        content = data["choices"][0]["message"]["content"].strip()

        # Map search result references to markdown links.
        search_results = data.get("search_results", [])
        references = {
            str(idx + 1): f"[{res.get('title', 'source')}]({res.get('url', '')})"
            for idx, res in enumerate(search_results)
        }

        def _replace(match: re.Match[str]) -> str:
            key = match.group(1)
            return references.get(key, match.group(0))

        content = re.sub(r"\[(\d+)\]", _replace, content)
        data["choices"][0]["message"]["content"] = content

        return data
