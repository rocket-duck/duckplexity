import json
from pathlib import Path

DATA_DIR = Path("data")
ACCESS_FILE = DATA_DIR / "access.json"

def load_access() -> dict:
    DATA_DIR.mkdir(exist_ok=True)
    if ACCESS_FILE.exists():
        with ACCESS_FILE.open("r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_access(data: dict) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    with ACCESS_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f)
