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
from langchain.messages import ToolMessage

load_dotenv()


# Tool error handling

@wrap_tool_call
def handle_tool_errors(request, handler):
    """Handle tool execution errors with custom messages."""
    try:
        return handler(request)
    except Exception as e:
        # Return a custom error message to the model
        return ToolMessage(
            content=f"Tool error: Please check your input and try again. ({str(e)})",
            tool_call_id=request.tool_call["id"]
        )

# Tools definition

@tool("web_search", description="Performs a websearch using DuckDuckGo")
def duckduckgo_web_search(query: str) -> str:
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
    timeout=25,
    verbose=True
)

# Create the agent with checkpointer
checkpointer = InMemorySaver()
# agent_executor = create_agent(llm_model, [duckduckgo_web_search], checkpointer=checkpointer)
agent_executor = create_agent(
    model=llm_model,  # Pass the model object or string name
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
    ],
    checkpointer=checkpointer  # Kept as a top-level argument
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