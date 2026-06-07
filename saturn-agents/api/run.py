"""Simple runner for local development.

Usage:
    python -m api.run

This will run Uvicorn serving the FastAPI app at http://127.0.0.1:8000
"""

import uvicorn


def main() -> None:
    uvicorn.run("api.app:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()
