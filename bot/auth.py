import json
from pathlib import Path

ACCESS_FILE = Path("access.json")

def load_access() -> dict:
    if ACCESS_FILE.exists():
        with ACCESS_FILE.open("r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_access(data: dict) -> None:
    with ACCESS_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f)
