# Saturn
```
 ███████  █████  ████████ ██    ██ ██████  ███    ██ 
 ██      ██   ██    ██    ██    ██ ██   ██ ████   ██ 
 ███████ ███████    ██    ██    ██ ██████  ██ ██  ██ 
      ██ ██   ██    ██    ██    ██ ██   ██ ██  ██ ██ 
 ███████ ██   ██    ██     ██████  ██   ██ ██   ████ 
```

## Overview

Saturn is an agentic GraphRAG system for historical document analysis and reasoning. It turns source texts into a knowledge graph of entities, relationships, communities, and semantic embeddings so users can explore history through structured connections instead of just raw text.

The backend ingests documents, extracts entities and relationships with DeepSeek, writes them into Neo4j, detects community structure with Neo4j GDS / Leiden, creates hierarchical summaries, and stores semantic vectors in Qdrant for retrieval.

## Project structure

- `saturn-agents/` — Python backend package and API.
- `Saturn-UI/` — React + Vite user interface.
- `saturn-agents/docker-compose.yaml` — local Neo4j and Qdrant services.
- `volumes/` — persisted Neo4j and Qdrant data storage.

## Features

- Graph-based retrieval over historical documents
- Entity and relationship extraction with DeepSeek
- Knowledge graph storage in Neo4j
- Community detection using Neo4j GDS Leiden algorithm
- Vector embeddings in Qdrant for semantic search
- Browser UI for query-driven exploration

## Requirements

- Node.js and npm
- Python 3.11+
- Docker and Docker Compose (for Neo4j + Qdrant)
- DeepSeek and Google API keys

## Setup

1. Clone the repository.
2. Start the local graph/vector services:

```bash
cd saturn-agents
docker compose up -d
```

3. Install project dependencies from the root:

```bash
npm run install:all
```

If you prefer a manual install:

```bash
npm install
cd Saturn-UI && npm install
cd ../saturn-agents && pip install -e .
```

4. Create a `.env` file in `saturn-agents/` with your configuration values.

### Required `saturn-agents/.env` variables

```env
deepseek_api_key=your_deepseek_key
google_api_key=your_google_key
neo4j_uri=bolt://localhost:7687
neo4j_user=neo4j
neo4j_password=nilava1993
qdrant_host=localhost
qdrant_port=6333
qdrant_collection=graph_rag
chunk_size=1000
chunk_overlap=200
max_workers=4
embedding_model=gemini-embedding-2
embedding_dim=3072
deepseek_base_url=https://api.deepseek.ai
deepseek_model=deepseek-v4
```

> The backend loads `.env` from the `saturn-agents` folder via Pydantic Settings.

## Run locally

From the project root, start the backend and UI together:

```bash
npm run up
```

Or run them separately:

```bash
npm run api
npm run ui
```

- Backend: `http://127.0.0.1:8000`
- UI: `http://localhost:5173`

The UI is configured to proxy `/api` requests to the backend at `127.0.0.1:8000`.

## Backend details

- `saturn-agents/api/run.py` starts Uvicorn with `api.app:app`.
- `saturn-agents/config.py` defines all environment settings.
- Query and ingestion routes are exposed through FastAPI.

## UI details

- `Saturn-UI/` is a Vite React app.
- `Saturn-UI/src/lib/api.ts` posts user queries to `/api/query`.
- The UI renders graph and conversation results for query-driven exploration.

## Notes

- Make sure `docker compose` is running before starting the backend.
- Update your `.env` values for your actual API credentials and endpoint URLs.
- If you need a custom API URL for the UI, set `VITE_API_URL` in `Saturn-UI/.env`.

## References

- `saturn-agents/docker-compose.yaml` for local Neo4j and Qdrant setup.
- `package.json` scripts for installation and startup.


