from langchain.tools import tool
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

from config import get_settings

# Settings singleton
_settings = get_settings()
COLLECTION = _settings.qdrant_collection
EMBEDDING_MODEL = _settings.embedding_model

# Clients are created lazily to avoid hard failures at import time
_qdrant: QdrantClient | None = None
_gemini = None


def _get_qdrant() -> QdrantClient:
    global _qdrant
    if _qdrant is None:
        try:
            _qdrant = QdrantClient(host=_settings.qdrant_host, port=_settings.qdrant_port)
        except Exception as e:
            raise RuntimeError(f"Failed to create Qdrant client: {e}")
    return _qdrant


def _get_gemini():
    global _gemini
    if _gemini is None:
        try:
            from google import genai

            _gemini = genai.Client(api_key=_settings.google_api_key)
        except Exception as e:
            raise RuntimeError(f"Failed to create Gemini client: {e}")
    return _gemini


def _embed(text: str) -> list[float]:
    gem = _get_gemini()
    from google.genai import types as genai_types

    resp = gem.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=genai_types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
    )
    return resp.embeddings[0].values


@tool
def search_qdrant(query: str, level: str = "low", top_k: int = 5) -> str:
    """
    Embed the query and search Qdrant for semantically relevant community
    summaries and document chunks.

    level options:
    - 'root' → broad / thematic questions
    - 'low'  → specific / factual questions  (default)
    - 'high' → mid-level conceptual questions

    Falls back to unfiltered search if no results found for the given level.
    """
    try:
        vector = _embed(query)

        # filtered search
        q = _get_qdrant()
        hits = q.search(
            collection_name=COLLECTION,
            query_vector=vector,
            query_filter=Filter(
                must=[FieldCondition(key="level", match=MatchValue(value=level))]
            ),
            limit=top_k,
            with_payload=True,
        )

        # fallback — unfiltered
        if not hits:
            hits = q.search(
                collection_name=COLLECTION,
                query_vector=vector,
                limit=top_k,
                with_payload=True,
            )

        if not hits:
            return "No relevant chunks found in Qdrant."

        lines = []
        for i, hit in enumerate(hits, 1):
            text   = hit.payload.get("text") or hit.payload.get("community_summary", "")
            source = hit.payload.get("source", "unknown")
            lvl    = hit.payload.get("level", "—")
            score  = round(hit.score, 4)
            lines.append(f"[{i}] source={source} level={lvl} score={score}\n{text}")
        return "\n\n".join(lines)

    except Exception as e:
        return f"Qdrant error: {e}"