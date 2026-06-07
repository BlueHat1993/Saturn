import json
import logging
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_core.messages import AIMessage, ToolMessage

# Ensure the repository root is on sys.path so sibling packages can be imported
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from query.graph_rag_query import search

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


@tool
def search_knowledge_base(query: str) -> str:
    """Search the knowledge base for relevant information about the query."""
    logger.info("search_knowledge_base called with query=%r", query)
    results = search(query, top_k=5)
    logger.info("returned %d results", len(results))
    return json.dumps(results)


def answer_query(user_query: str) -> dict:
    """Answer a user query using the search agent and return the raw result plus tool output."""
    logger.info("answer_query called with query=%r", user_query)
    
    tools = [search_knowledge_base]
    
    agent = create_agent(
        model="deepseek:deepseek-chat",
        tools=tools,
        system_prompt="You are a helpful assistant that answers questions by searching a knowledge base. "
                      "Use the search_knowledge_base tool to find relevant information, then provide a clear answer."
                      "if you don't get a response from tool, say you don't know the answer.This is mandatory."
                      "DO NOT make up answers if the tool doesn't return relevant information.",
    )
    
    result = agent.invoke(
        {"messages": [{"role": "user", "content": user_query}]}
    )

    messages = result.get("messages", [])

    tool_response = [
        msg.content for msg in messages if isinstance(msg, ToolMessage)
    ]

    answer = "No answer generated"
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content:
            answer = msg.content
            break

    logger.info("answer generated")
    return {"tool_response": tool_response, "answer": answer}


# if __name__ == "__main__":
#     import sys
#     import json

#     if len(sys.argv) > 1:
#         query = " ".join(sys.argv[1:])
#     else:
#         query = input("Enter your question: ")

#     result = answer_query(query)
#     print("\n" + "=" * 60)
#     print("RESPONSE:")
#     print("=" * 60)
#     print(json.dumps(result, indent=2))
