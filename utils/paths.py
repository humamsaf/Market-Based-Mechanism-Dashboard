from pathlib import Path

def repo_root() -> Path:
    # .../utils/paths.py -> repo root
    return Path(__file__).resolve().parents[1]

def data_path(filename: str) -> str:
    return str(repo_root() / "data" / filename)
