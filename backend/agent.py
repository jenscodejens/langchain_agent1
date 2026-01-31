from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage, SystemMessage, AIMessage
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, END

from typing import Annotated, Sequence, TypedDict
from dotenv import load_dotenv
import logging
import re
from pathlib import Path

load_dotenv()
logger = logging.getLogger(__name__)

from config.llm_config import embeddings, llm_model
from tools import (
    shared_tools, github_tools, comms_tools, general_tools,
    github_agent_tools, comms_agent_full_tools, general_full_tools,
    github_agent_tool_dict, comms_agent_tool_dict, general_tool_dict
)

class AgentState(TypedDict):
    """State for the agent graph, containing messages."""
    messages: Annotated[Sequence[BaseMessage], add_messages]

# Bind LLMs to specific tool sets
github_agent_llm = llm_model.bind_tools(github_agent_tools)
comms_agent_llm = llm_model.bind_tools(comms_agent_full_tools)
general_llm = llm_model.bind_tools(general_full_tools)
supervisor_llm = llm_model  # No tools for supervisor

def _execute_tools(state, tool_dict):
    """Execute tools based on the last message's tool calls."""
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

# Tool executors for each agent
def github_agent_tool_exec(state):
    return _execute_tools(state, github_agent_tool_dict)

def comms_agent_tool_exec(state):
    return _execute_tools(state, comms_agent_tool_dict)

def general_tool_exec(state):
    return _execute_tools(state, general_tool_dict)

# Agent call functions
def github_agent_call(state):
    system_prompt_content = Path('config/system_prompt_github.txt').read_text(encoding='utf-8')
    system_prompt = SystemMessage(content=system_prompt_content)
    
    response = github_agent_llm.invoke([system_prompt] + state["messages"])
    return {"messages": [response]}

def comms_agent_call(state):
    system_prompt_content = Path('config/system_prompt_comms_agent.txt').read_text(encoding='utf-8')
    system_prompt = SystemMessage(content=system_prompt_content)
    
    response = comms_agent_llm.invoke([system_prompt] + state["messages"])
    return {"messages": [response]}

def general_call(state):
    # General agent with no special system prompt
    response = general_llm.invoke(state["messages"])
    return {"messages": [response]}

# Supervisor function
def supervisor(state):
    messages = state["messages"]
    query = messages[-1].content
    
    # Input sanitization
    query = re.sub(r'[<>"\\]', '', query)
    
    # Keyword-based routing
    if any(word in query.lower() for word in ["github", "repo", "issue", "pull"]):
        next_node = "github_agent"
    elif any(word in query.lower() for word in ["email", "message", "notify", "comms"]):
        next_node = "comms_agent"
    else:
        # LLM-based classification
        prompt = f"""Classify query: {query}
Options: github_agent (GitHub), comms_agent (email/msg), general (other). Respond ONLY with the agent name."""
        response = supervisor_llm.invoke([SystemMessage(content="You are a query classifier. Respond only with the agent name."), HumanMessage(content=prompt)])
        next_node = response.content.strip().lower()
        if next_node not in ["github_agent", "comms_agent", "general"]:
            next_node = "general"  # fallback
    
    logger.info(f"Routing '{query[:50]}...' to {next_node}")
    return {"next": next_node, "messages": [AIMessage(content=f"Routed to {next_node}")]}

# Graph construction
graph = StateGraph(AgentState)
graph.add_node("supervisor", supervisor)
graph.add_node("github_agent", github_agent_call)
graph.add_node("github_agent_tools", github_agent_tool_exec)
graph.add_node("comms_agent", comms_agent_call)
graph.add_node("comms_agent_tools", comms_agent_tool_exec)
graph.add_node("general", general_call)
graph.add_node("general_tools", general_tool_exec)

graph.set_entry_point("supervisor")

# Supervisor routing
graph.add_conditional_edges(
    "supervisor",
    lambda state: state.get("next", "general"),
    {"github_agent": "github_agent", "comms_agent": "comms_agent", "general": "general", "__end__": END}
)

# Helper function for agent loops
def should_continue(state):
    last_msg = state["messages"][-1]
    return "tools" if last_msg.tool_calls else "supervisor"

# Agent loops
graph.add_conditional_edges("github_agent", should_continue, {"tools": "github_agent_tools", "supervisor": "supervisor"})
graph.add_edge("github_agent_tools", "github_agent")

graph.add_conditional_edges("comms_agent", should_continue, {"tools": "comms_agent_tools", "supervisor": "supervisor"})
graph.add_edge("comms_agent_tools", "comms_agent")

graph.add_conditional_edges("general", should_continue, {"tools": "general_tools", "supervisor": "supervisor"})
graph.add_edge("general_tools", "general")

# Compile the graph
app = graph.compile(checkpointer=InMemorySaver())

config = {"configurable": {"thread_id": "conversation_1"}}
