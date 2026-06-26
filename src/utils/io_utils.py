from pathlib import Path
import json


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def safe_json_load(path: str | Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
