"""Run the FastAPI app for local development.

Usage (from the saturn-agents project root):
    python -m api.run
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure saturn-agents is on sys.path so `agents`, `query`, and `api` resolve
# consistently regardless of how the process is started.
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import uvicorn


def main() -> None:
    uvicorn.run("api.app:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()
