import os
from dotenv import load_dotenv
from langchain_xai import ChatXAI
from langchain.tools import tool
from ddgs import DDGS
from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware
from langgraph.checkpoint.memory import InMemorySaver
from langchain.chat_models import init_chat_model
from langchain.messages import HumanMessage, AIMessage, SystemMessage

load_dotenv()

# Initialize the Grok model
llm_model = ChatXAI(
    model="grok-4-1-fast-reasoning",
    temperature=0.5,
    timeout=25,
    verbose=True
)

system_msg = SystemMessage("""
You are a helpful chat bot.
Always explain your reasoning if it is a complex answer and if you dont know the answer you say so.
""")

@tool
def duckduckgo_web_search(query: str) -> str:
    """Search DuckDuckGo for the given query and return text results."""
    try:
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=1)]
        if results:
            return results[0].get('body', 'No body found')
        else:
            return "No results found"
    except Exception as e:
        return f"Error during search: {str(e)}"
    
agent = create_agent(
    model="llm_model",
    tools=[duckduckgo_web_search],
    middleware=[
        SummarizationMiddleware(
            model="llm_model",
            trigger=[
                ("tokens", 3000),
                ("messages", 8),
            ],
            keep=("messages", 20),
        ),
    ],
)

   
if __name__ == "__main__":
    user_query = input("Enter your DuckDuckGo search phrase: ")
    output = duckduckgo_web_search.invoke(user_query) 
    print("\nSearch results:\n")
    print(output)
