from pathlib import Path
import json


def ensure_dir(path: str | Path) -> Path:
    """Create the directory (and parents) if it doesn't already exist."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def safe_json_load(path: str | Path):
    """Read and parse a JSON file. Assumes UTF-8 encoding."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
