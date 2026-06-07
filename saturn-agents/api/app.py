from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agents import saturn_graph

app = FastAPI(
    title="Saturn Graph RAG API",
    description="Run the Saturn agentic graph RAG workflow. Use the `/query` endpoint."
)


class QueryRequest(BaseModel):
    query: str = Field(..., example="Who are the main entities related to 'Acme Corp'?")


def _invoke_graph_workflow(query: str) -> Dict[str, Any]:
    """Invoke the Saturn graph workflow.

    Prefer using the compiled graph when possible; if the graph raises a
    concurrent-update error (seen with langgraph when nodes update the same
    keys in parallel), fall back to a sequential execution of the node
    functions defined in `agents.saturn_graph`.
    """
    state = {"user_query": query}

    g = saturn_graph.graph_rag_app

    # First try invoking the compiled graph object in the natural way.
    try:
        if callable(g):
            return g(state) or {}
    except Exception as e:
        # If the graph engine complains about concurrent updates (multiple
        # values for the same key when nodes run in parallel), we'll fall
        # back to a safe sequential execution below.
        err_text = str(e)
        if "Can receive only one value per step" not in err_text:
            # unknown error — re-raise to surface to caller
            raise

    # Sequential fallback: import and run nodes directly to avoid parallel
    # conflicts. This executes the same logic order as the graph but
    # deterministically.
    try:
        from agents.saturn_graph import (
            decompose_node,
            neo4j_node,
            qdrant_node,
            synthesis_node,
        )

        state = decompose_node(state)
        state = neo4j_node(state)
        state = qdrant_node(state)
        state = synthesis_node(state)
        return state or {}
    except Exception as e:  # pragma: no cover - defensive
        raise RuntimeError(f"Unable to invoke graph workflow: {e}")


@app.post("/query")
async def query_graph(req: QueryRequest) -> Dict[str, Any]:
    """Run the Saturn graph RAG workflow for a user query and return the state.

    Use the interactive Swagger UI at `/docs` to POST JSON bodies.
    """
    try:
        result = _invoke_graph_workflow(req.query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if isinstance(result, dict):
        return result
    if isinstance(result, str):
        return {"result": result}

    return {"result": str(result)}


@app.get("/query")
async def query_get(q: str):
    """Convenience GET endpoint: /query?q=..."""
    return await query_graph(QueryRequest(query=q))



# CORS — allow Swagger UI or external pages to call the API during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    """Redirect root to the interactive docs for convenience."""
    return RedirectResponse(url="/docs")
