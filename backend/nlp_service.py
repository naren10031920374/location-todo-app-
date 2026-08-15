import requests
import json
from typing import Optional, Dict, Any

# Ollama API endpoint
OLLAMA_URL = "http://localhost:11434/api/generate"

def parse_todo_text(text: str) -> Dict[str, Any]:
    """
    Parse natural language todo text using Ollama
    
    Example input: "I need milk, eggs, and bread from Walmart tomorrow"
    Example output: {
        "items": ["milk", "eggs", "bread"],
        "store": "Walmart",
        "date": "tomorrow",
        "category": "groceries"
    }
    
    Args:
        text: Natural language todo description
    
    Returns:
        Dictionary with parsed fields
    """
    
    # Prompt for Ollama to parse the todo
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
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": "mistral",
                "prompt": prompt,
                "stream": False,
                "temperature": 0.1  # Low temperature for consistent parsing
            },
            timeout=30
        )
        
        if response.status_code != 200:
            return {"error": f"Ollama error: {response.status_code}"}
        
        result = response.json()
        response_text = result.get("response", "").strip()
        
        # Try to extract JSON from response
        try:
            # Find JSON in response (sometimes model adds extra text)
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}") + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                parsed = json.loads(json_str)
                return parsed
            else:
                return {"error": "No JSON found in response"}
        
        except json.JSONDecodeError as e:
            return {"error": f"Failed to parse JSON: {str(e)}", "raw_response": response_text}
    
    except requests.exceptions.RequestException as e:
        return {"error": f"Ollama connection error: {str(e)}"}

def classify_todo_category(text: str) -> Optional[str]:
    """
    Classify a todo into a category using Ollama
    
    Args:
        text: Todo text
    
    Returns:
        Category string (groceries, pharmacy, hardware, etc.) or None
    """
    
    prompt = f"""Classify this todo into ONE category. Return only the category name, nothing else.

Todo: "{text}"

Categories: groceries, pharmacy, hardware, clothing, entertainment, other

Category:"""
    
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": "mistral",
                "prompt": prompt,
                "stream": False,
                "temperature": 0.1
            },
            timeout=10
        )
        
        if response.status_code != 200:
            return None
        
        result = response.json()
        category = result.get("response", "").strip().lower()
        
        valid_categories = ["groceries", "pharmacy", "hardware", "clothing", "entertainment", "other"]
        
        if category in valid_categories:
            return category
        
        return "other"
    
    except requests.exceptions.RequestException:
        return None

def suggest_stores_for_item(item: str) -> list[str]:
    """
    Suggest stores that typically sell an item using Ollama
    
    Args:
        item: Item name (e.g., "milk", "headphones")
    
    Returns:
        List of store names
    """
    
    prompt = f"""Suggest 2-3 common stores in the USA that typically sell "{item}".

Return ONLY a JSON array of store names, no explanation.

Example: ["Walmart", "Target", "Amazon"]

Stores:"""
    
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": "mistral",
                "prompt": prompt,
                "stream": False,
                "temperature": 0.1
            },
            timeout=10
        )
        
        if response.status_code != 200:
            return []
        
        result = response.json()
        response_text = result.get("response", "").strip()
        
        # Extract JSON array
        start_idx = response_text.find("[")
        end_idx = response_text.rfind("]") + 1
        
        if start_idx != -1 and end_idx > start_idx:
            json_str = response_text[start_idx:end_idx]
            stores = json.loads(json_str)
            return stores if isinstance(stores, list) else []
        
        return []
    
    except (requests.exceptions.RequestException, json.JSONDecodeError):
        return []