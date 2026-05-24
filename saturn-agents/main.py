from langchain.agents import create_agent 
from dotenv import load_dotenv

load_dotenv()

agent = create_agent(
        model="deepseek:deepseek-chat",
        tools=[],
        system_prompt="You are a helpful assistant that provides information about the world."
)


if __name__ == "__main__":
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "Hi,how are you?"}]}
    )
    print(result["messages"][-1].text)
