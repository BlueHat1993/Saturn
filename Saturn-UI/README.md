# Saturn UI

Interactive frontend for the Saturn search agent: chat on the left, knowledge graph on the right.

## Features

- **Chat** — sends queries to `POST /query` and displays the agent answer
- **Graph** — parses `tool_response` into nodes (search hits), colors nodes by community, and draws weighted edges based on text similarity
- **Hover** — canvas tooltip plus a detail panel with full node text

## Run

1. Start the API (from `saturn-agents`):

   ```bash
   python -m api.run
   ```

2. Start the UI:

   ```bash
   cd Saturn-UI
   npm install
   npm run dev
   ```

3. Open the URL shown by Vite (usually `http://localhost:5173`).

The dev server proxies `/api` to `http://127.0.0.1:8000`. Set `VITE_API_URL` if your API runs elsewhere.
