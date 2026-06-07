Quick API for the Saturn agentic graph workflow

Endpoints
- POST /query  — JSON body: {"query": "your question"}
- GET  /query?q=... — convenience wrapper

Run
```
python -m api.run
# or with uvicorn directly
uvicorn api.app:app --reload
```

Notes
- The endpoint invokes the compiled agent graph in `agents.saturn_graph.graph_rag_app`.
- The server attempts several invocation styles (`call`, `run`, `invoke`) to be
  tolerant of different graph object implementations.
