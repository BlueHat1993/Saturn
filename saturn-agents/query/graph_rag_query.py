import logging
import os
from dotenv import load_dotenv
from google import genai
from qdrant_client import QdrantClient

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

gemini = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
qdrant = QdrantClient(host=os.getenv("QDRANT_HOST", "localhost"), port=int(os.getenv("QDRANT_PORT", 6333)))
COLLECTION = os.getenv("QDRANT_COLLECTION", "graph_rag")


def search(query: str, top_k: int = 5) -> list[dict]:
    logger.info("search called with query=%r top_k=%d", query, top_k)
    vector = gemini.models.embed_content(model="gemini-embedding-2", contents=query).embeddings[0].values
    logger.debug("embedded query vector length=%d", len(vector))
    hits = qdrant.query_points(collection_name=COLLECTION, query=vector, limit=top_k, with_payload=True).points
    logger.info("qdrant search returned %d hits for collection=%s", len(hits), COLLECTION)
    results = [{"id": h.id, "score": round(h.score, 4), "payload": h.payload} for h in hits]
    logger.debug("search results=%s", results)
    return results


if __name__ == "__main__":
    import sys
    for r in search(" ".join(sys.argv[1:])):
        print(r)