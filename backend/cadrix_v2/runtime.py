"""Runtime paths shared by legacy and V2 exports."""
import os
from pathlib import Path


def output_directory() -> Path:
    path = Path(os.environ.get("CADRIX_OUTPUT_DIR") or Path(__file__).resolve().parent.parent / "out").resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path
