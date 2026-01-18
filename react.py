from datetime import datetime
from langchain_xai import ChatXAI
from langchain.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents.middleware import SummarizationMiddleware
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage, SystemMessage
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, END

from typing import Annotated, Sequence, TypedDict
from dotenv import load_dotenv
from ddgs import DDGS
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper

import logging

load_dotenv()
logger = logging.getLogger(__name__)
ddg_api = DuckDuckGoSearchAPIWrapper(max_results=3)


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages] # provides the meta data

@tool("get_date_and_time", description="Returns the current date and time")
def current_datetime():
    """Returns the current date and time in YYYY-MM-DD HH:MM format.""" 
    return datetime.now().strftime("%Y-%m-%d %H:%M")

@tool("web_search", description="Performs a websearch using DuckDuckGo")
def duckduckgo_web_search(query: str) -> str:
    """Useful for searching current events or facts not in your training data.
    Input should be a specific search query.
    """
    # print(f"\t[-Debug Tool used: {duckduckgo_web_search.name}: {query}]") # debug purpose
    try:
        # Use the standard wrapper for cleaner result handling
        return ddg_api.run(query)
    except Exception as e:
        # Let the middleware handle the exception bubble-up
        raise RuntimeError(f"Search failed for query '{query}': {str(e)}")

tools = [duckduckgo_web_search, current_datetime]
tool_dict = {tool.name: tool for tool in tools}

def custom_tool_executor(state: AgentState) -> AgentState:
    messages = state["messages"]
    last_message = messages[-1]
    tool_calls = last_message.tool_calls
    tool_results = []
    for tool_call in tool_calls:
        tool_name = tool_call["name"]
        tool = tool_dict.get(tool_name)
        if tool:
            try:
                result = tool.invoke(tool_call)
                tool_results.append(ToolMessage(content=str(result), tool_call_id=tool_call["id"]))
            except Exception as e:
                logger.error(f"Tool '{tool_name}' failed: {e}")
                tool_results.append(ToolMessage(content=f"Error: {str(e)}", tool_call_id=tool_call["id"], status="error"))
        else:
            tool_results.append(ToolMessage(content=f"Unknown tool: {tool_name}", tool_call_id=tool_call["id"], status="error"))
    return {"messages": tool_results}


llm_model = ChatXAI(    
    model="grok-4-1-fast-reasoning",
    temperature=0.5,
    timeout=25,
    verbose=True
).bind_tools(tools)


def model_call(state:AgentState) -> AgentState:
    system_prompt = SystemMessage(content=
        "You are a helpfull AI assistant. Please answer my query to the best of your ability, If you dont know the answer ask for more context if needed. Use semojis only moderatly when appropriate."
    )
    response = llm_model.invoke([system_prompt] + state["messages"])
    return{"messages": [response]}

def should_iterate(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]
    if not last_message.tool_calls:

        return "end"
    else:
        return "iterate"

graph = StateGraph(AgentState)
graph.add_node("agent1", model_call)

graph.add_node("tools", custom_tool_executor)

graph.set_entry_point("agent1")

graph.add_conditional_edges(
    "agent1",
    should_iterate,
    {
        "iterate": "tools",
        "end": END,
    }
)

graph.add_edge("tools", "agent1")

app = graph.compile()

def print_stream(stream):
    for s in stream:
        for node_output in s.values():
            for message in node_output.get("messages", []):
                message.pretty_print()

# inputs = {"messages": [HumanMessage(content="What is the temperature in Göteborg Sweden now")]}


inputs = {"messages": [
    # HumanMessage(content="what date is it"),
    HumanMessage(content="what date is it and what is the temperature in Göteborg Sweden currently.")
]}

for msg in inputs["messages"]:
    msg.pretty_print()
print_stream(app.stream(inputs, stream_mode="updates"))