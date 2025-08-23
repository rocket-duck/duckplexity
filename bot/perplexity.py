import os
import json
import logging
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
    logging.info("Perplexity API request: %s", json.dumps(payload, ensure_ascii=False))
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(API_URL, headers=headers, json=payload)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            # Surface API error details for easier debugging
            raise RuntimeError(f"Perplexity API error: {response.text}") from exc
        logging.info("Perplexity API raw response: %s", response.text)
        data: Dict[str, Any] = response.json()
        logging.info("Perplexity API parsed response: %s", json.dumps(data, ensure_ascii=False))
        content = data["choices"][0]["message"]["content"].strip()

        # Collect footnote-style reference list so callers can easily strip
        # or hyperlink them later.
        search_results = data.get("search_results", [])
        urls = [res.get("url", "") for res in search_results]

        if urls:
            footnotes = [f"[{idx}]: {url}" for idx, url in enumerate(urls, start=1)]
            content = content + "\n\n" + "\n".join(footnotes)
        data["choices"][0]["message"]["content"] = content

        return data
