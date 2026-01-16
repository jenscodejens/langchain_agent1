import os
from dotenv import load_dotenv
from langchain_xai import ChatXAI
from langchain.tools import tool
from ddgs import DDGS
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import HumanMessage

load_dotenv()

# Define the tool
@tool
def duckduckgo_web_search(query: str) -> str:
    """Search DuckDuckGo for the given query and return text results."""
    try:
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=1)]
        if results:
            print(f"\t[Tool used: {duckduckgo_web_search.name}: {query}]")
            return results[0].get('body', 'No body found')
        else:
            return "No results found"
    except Exception as e:
        return f"Error during search: {str(e)}"

# Initialize the LLM
llm_model = ChatXAI(
    model="grok-4-1-fast-reasoning",
    temperature=0.5,
    timeout=25
)

# Create the agent with checkpointer
checkpointer = InMemorySaver()
agent_executor = create_agent(llm_model, [duckduckgo_web_search], checkpointer=checkpointer)

if __name__ == "__main__":
    print("Chat with the agent. Type 'exit' to quit.")
    config = {"configurable": {"thread_id": "chat_session"}}
    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            break
        response = agent_executor.invoke({"messages": [HumanMessage(content=user_input)]}, config)
        print(f"Agent: {response['messages'][-1].content}")