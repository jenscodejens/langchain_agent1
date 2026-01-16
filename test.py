import os
from dotenv import load_dotenv
from langchain_xai import ChatXAI
from langchain.tools import tool
from ddgs import DDGS
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents.middleware import SummarizationMiddleware
from langchain_core.messages import HumanMessage
from langchain.agents.middleware import wrap_tool_call
from langchain_core.messages import ToolMessage
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
import logging

load_dotenv()
logger = logging.getLogger(__name__)
ddg_api = DuckDuckGoSearchAPIWrapper(max_results=3)

# Tool error handling

@wrap_tool_call
def handle_tool_errors(request, handler):
    """Handle tool execution with logging and distinct error feedback."""
    try:
        # Pass the request to the actual tool execution
        return handler(request)
    except Exception as e:
        # Log the full stack trace for debugging
        logger.error(f"Tool '{request.tool.name}' failed: {e}", exc_info=True)
        
        # Determine if it's an error the LLM can fix (input error) 
        # or a system error (API down)
        error_msg = f"System Error: The tool '{request.tool.name}' is temporarily unavailable."
        if "validation" in str(e).lower():
            error_msg = f"Input Error: {str(e)}. Please correct your arguments."

        return ToolMessage(
            content=error_msg,
            tool_call_id=request.tool_call["id"],
            status="error" # Metadata to signal failure to the agent
        )

# Tools definition

@tool("web_search", description="Performs a websearch using DuckDuckGo")
def duckduckgo_web_search(query: str) -> str:
    """Useful for searching current events or facts not in your training data.
    Input should be a specific search query.
    """
    print(f"\t[-Debug Tool used: {duckduckgo_web_search.name}: {query}]") # debug purpose
    try:
        # Use the standard wrapper for cleaner result handling
        return ddg_api.run(query)
    except Exception as e:
        # Let the middleware handle the exception bubble-up
        raise RuntimeError(f"Search failed for query '{query}': {str(e)}")

# Initialize the LLM
llm_model = ChatXAI(
    model="grok-4-1-fast-reasoning",
    temperature=0.5,
    timeout=25,
    verbose=True
)

# Create the agent with checkpointer
checkpointer = InMemorySaver()

agent_executor = create_agent(
    model=llm_model, 
    tools=[duckduckgo_web_search],
    middleware=[
        SummarizationMiddleware(
            model=llm_model,
            trigger=[
                ("tokens", 3000),
                ("messages", 10),
            ],
            keep=("messages", 5),
        ),
        handle_tool_errors
    ],
    checkpointer=checkpointer
)


if __name__ == "__main__":
    print("Chat with the agent. Type 'exit' to quit.")
    config = {"configurable": {"thread_id": "chat_session"}}
    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            break
        response = agent_executor.invoke({"messages": [HumanMessage(content=user_input)]}, config)
        print(f"Agent: {response['messages'][-1].content}")