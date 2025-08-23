import os
import re
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

        # Map numeric reference placeholders to Markdown links without titles and
        # collect footnote-style reference list.
        search_results = data.get("search_results", [])
        urls = [res.get("url", "") for res in search_results]

        # Replace occurrences like [1] in the content with a hyperlink [1](url)
        link_map = {str(idx): f"[{idx}]({url})" for idx, url in enumerate(urls, start=1)}

        def _replace(match: re.Match[str]) -> str:
            key = match.group(1)
            return link_map.get(key, match.group(0))

        content = re.sub(r"\[(\d+)\]", _replace, content)
        # Append the list of sources at the end separated by newlines using
        # footnote-style `[n]: url` entries so that callers can easily strip
        # them if desired.
        if urls:
            footnotes = [f"[{idx}]: {url}" for idx, url in enumerate(urls, start=1)]
            content = content + "\n\n" + "\n".join(footnotes)
        data["choices"][0]["message"]["content"] = content

        return data
