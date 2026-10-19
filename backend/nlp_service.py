"""
LLM-backed helpers: todo parsing, category classification, store suggestions.

Talks to any OpenAI-compatible chat completions API. Groq is the default;
the provider is chosen purely through environment variables:

    LLM_API_KEY    API key (GROQ_API_KEY is also accepted)
    LLM_BASE_URL   default: https://api.groq.com/openai/v1
    LLM_MODEL      default: openai/gpt-oss-20b

A local Ollama server also works for development without a key:
    LLM_BASE_URL=http://localhost:11434/v1  LLM_MODEL=mistral
"""
import json
import os
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

DEFAULT_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_MODEL = "openai/gpt-oss-20b"

VALID_CATEGORIES = ["groceries", "pharmacy", "hardware", "clothing", "entertainment", "other"]


class LLMError(Exception):
    """Raised when the LLM is not configured, unreachable, or returns an error."""


def _settings() -> Dict[str, str]:
    """Read settings at call time so tests and env changes take effect."""
    return {
        "base_url": os.getenv("LLM_BASE_URL", DEFAULT_BASE_URL).rstrip("/"),
        "api_key": os.getenv("LLM_API_KEY") or os.getenv("GROQ_API_KEY") or "",
        "model": os.getenv("LLM_MODEL", DEFAULT_MODEL),
    }


def _is_local(base_url: str) -> bool:
    return "localhost" in base_url or "127.0.0.1" in base_url


def _chat(prompt: str, timeout: int = 20) -> str:
    """Send one user prompt to the chat completions API and return the reply text."""
    cfg = _settings()

    # Hosted providers need a key; a local server (e.g. Ollama) does not.
    if not cfg["api_key"] and not _is_local(cfg["base_url"]):
        raise LLMError("LLM is not configured: set LLM_API_KEY")

    headers = {"Content-Type": "application/json"}
    if cfg["api_key"]:
        headers["Authorization"] = f"Bearer {cfg['api_key']}"

    try:
        response = requests.post(
            f"{cfg['base_url']}/chat/completions",
            headers=headers,
            json={
                "model": cfg["model"],
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,  # low temperature for consistent parsing
            },
            timeout=timeout,
        )
    except requests.exceptions.RequestException as e:
        raise LLMError(f"LLM connection error: {e}") from e

    if response.status_code != 200:
        raise LLMError(f"LLM error: HTTP {response.status_code}")

    try:
        content = response.json()["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError) as e:
        raise LLMError("LLM returned an unexpected response format") from e

    return (content or "").strip()


def parse_todo_text(text: str) -> Dict[str, Any]:
    """
    Parse natural language todo text.

    Example input: "I need milk, eggs, and bread from Walmart tomorrow"
    Example output: {
        "items": ["milk", "eggs", "bread"],
        "store": "Walmart",
        "date": "tomorrow",
        "category": "groceries"
    }

    Returns a dict with the parsed fields, or {"error": ...} on failure.
    """
    prompt = f"""Parse this todo text and extract structured information.

Todo text: "{text}"

Return ONLY a JSON object (no markdown, no explanation) with these fields:
- items: list of items to buy (array of strings)
- store: store name if mentioned (string or null)
- date: when to do it if mentioned (string or null)
- category: category of items if obvious (string or null, e.g. "groceries", "pharmacy", "hardware")

Important: Return ONLY valid JSON, nothing else.

JSON:"""

    try:
        response_text = _chat(prompt, timeout=30)
    except LLMError as e:
        return {"error": str(e)}

    # Models sometimes wrap the JSON in extra text; pull out the outermost object.
    start_idx = response_text.find("{")
    end_idx = response_text.rfind("}") + 1
    if start_idx == -1 or end_idx <= start_idx:
        return {"error": "No JSON found in response"}

    try:
        parsed = json.loads(response_text[start_idx:end_idx])
    except json.JSONDecodeError as e:
        return {"error": f"Failed to parse JSON: {e}", "raw_response": response_text}

    if not isinstance(parsed, dict):
        return {"error": "Unexpected JSON shape in response"}
    return parsed


def classify_todo_category(text: str) -> Optional[str]:
    """
    Classify a todo into one category.

    Returns one of VALID_CATEGORIES, "other" if the model answers with
    something else, or None if the LLM is unavailable.
    """
    prompt = f"""Classify this todo into ONE category. Return only the category name, nothing else.

Todo: "{text}"

Categories: {", ".join(VALID_CATEGORIES)}

Category:"""

    try:
        reply = _chat(prompt, timeout=10)
    except LLMError:
        return None

    category = reply.strip().strip('."\'').lower()
    return category if category in VALID_CATEGORIES else "other"


def suggest_stores_for_item(item: str) -> list[str]:
    """Suggest 2-3 common US stores that sell an item. Returns [] on any failure."""
    prompt = f"""Suggest 2-3 common stores in the USA that typically sell "{item}".

Return ONLY a JSON array of store names, no explanation.

Example: ["Walmart", "Target", "Amazon"]

Stores:"""

    try:
        reply = _chat(prompt, timeout=10)
    except LLMError:
        return []

    start_idx = reply.find("[")
    end_idx = reply.rfind("]") + 1
    if start_idx == -1 or end_idx <= start_idx:
        return []

    try:
        stores = json.loads(reply[start_idx:end_idx])
    except json.JSONDecodeError:
        return []

    return [s for s in stores if isinstance(s, str)] if isinstance(stores, list) else []
