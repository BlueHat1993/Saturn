from langchain.agents import create_agent
from langchain_deepseek import ChatDeepSeek
from agents.tools.qdrant_tool import search_qdrant
from langchain_core.messages import HumanMessage

qdrant_agent = create_agent(
    ChatDeepSeek(model="deepseek-chat", temperature=0),
    tools=[search_qdrant],
    name="qdrant_agent",
    system_prompt="""You are a semantic retrieval expert. Find the most relevant
document chunks and community summaries from Qdrant to answer questions.

Level selection guide:
- level='root' → broad, thematic, high-level questions
- level='low'  → specific, factual, detail-oriented questions
- level='high' → mid-level conceptual questions

Rules:
- Pick the most appropriate level for the question.
- If the first search returns poor or irrelevant results, retry with a
  different level before giving up.
- Summarise the retrieved chunks into a coherent, grounded answer.""",
)


