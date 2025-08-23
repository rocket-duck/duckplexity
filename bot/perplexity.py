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

        # Map numeric reference placeholders to Markdown links without titles.
        search_results = data.get("search_results", [])
        links = [f"[{idx}]({res.get('url', '')})" for idx, res in enumerate(search_results, start=1)]

        # Replace occurrences like [1] in the content with a hyperlink [1](url)
        link_map = {str(idx): link for idx, link in enumerate(links, start=1)}

        def _replace(match: re.Match[str]) -> str:
            key = match.group(1)
            return link_map.get(key, match.group(0))

        content = re.sub(r"\[(\d+)\]", _replace, content)
        # Append the list of sources at the end separated by newlines
        if links:
            content = content + "\n\n" + "\n".join(links)
        data["choices"][0]["message"]["content"] = content

        return data
