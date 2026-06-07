from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from agents.search_agent import answer_query

app = FastAPI(
    title="Saturn Search Agent API",
    description="Query the knowledge base via the search agent. Use the `/query` endpoint.",
)


class QueryRequest(BaseModel):
    query: str = Field(..., examples=["Who are the main entities related to Acme Corp?"])


class QueryResponse(BaseModel):
    tool_response: list[str]
    answer: str


@app.post("/query", response_model=QueryResponse)
def query_search(req: QueryRequest) -> dict[str, Any]:
    """Run the search agent for a user query and return tool output plus the final answer."""
    try:
        return answer_query(req.query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")
