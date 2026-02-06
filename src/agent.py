from pydantic import BaseModel, Field
from typing import Literal, Annotated, Sequence, TypedDict, cast
from pathlib import Path
import logging

from dotenv import load_dotenv

# Configure logging to file
logging.basicConfig(filename='logs/agent.log', level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages 
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage, SystemMessage, AIMessage

# Import configuration and tools
from config.llm_config import llm_model
from src.tools import (
    github_agent_tools, comms_agent_tools,
    github_agent_tool_dict, comms_agent_tool_dict
)

load_dotenv()
logger = logging.getLogger(__name__)

# --- SCHEMA FOR STRUCTURED OUTPUT ---
class RouterResponse(BaseModel):
    """Logic for how the supervisor should route the query."""
    next_node: Literal["github_agent", "comms_agent", "ambiguous"] = Field(
        description="The next agent that should handle the query based on the user's intent."
    )
    reason: str = Field(description="A very compact reason.")

# Create the structured model for the supervisor
# Ensure your xAI model supports .with_structured_output (Grok-beta or later)
structured_supervisor = llm_model.with_structured_output(RouterResponse)

class AgentState(TypedDict):
    """State for the agent graph, containing messages."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    next: str  # Tracks the next node for conditional edges

# Bind LLMs to specific tool sets
github_agent_llm = llm_model.bind_tools(github_agent_tools)
comms_agent_llm = llm_model.bind_tools(comms_agent_tools)

def _execute_tools(state: AgentState, tool_dict: dict):
    """Execute tools based on the last message's tool calls."""
    messages = state["messages"]
    last_message = messages[-1]
    
    # Extract tool calls safely
    tool_calls = getattr(last_message, "tool_calls", [])
    tool_results = []
    
    for tool_call in tool_calls:
        tool_name = tool_call["name"]
        logger.info(f"Executing tool: {tool_name}")
        tool = tool_dict.get(tool_name)
        if tool:
            try:
                result = tool.invoke(tool_call)
                logger.info(f"Execution result: {str(result)[:200]}")
                tool_results.append(ToolMessage(content=str(result), tool_call_id=tool_call["id"]))
            except Exception as e:
                logger.error(f"Tool '{tool_name}' failed: {e}")
                tool_results.append(ToolMessage(content=f"Error: {str(e)}", tool_call_id=tool_call["id"], status="error"))
        else:
            tool_results.append(ToolMessage(content=f"Unknown tool: {tool_name}", tool_call_id=tool_call["id"], status="error"))
    return {"messages": tool_results}

# Tool executors
def github_agent_tool_exec(state: AgentState):
    return _execute_tools(state, github_agent_tool_dict)

def comms_agent_tool_exec(state: AgentState):
    return _execute_tools(state, comms_agent_tool_dict)

# Agent call functions
def github_agent_call(state: AgentState):
    prompt_path = Path('config/github_systemmessage.md')
    prompt = prompt_path.read_text(encoding='utf-8') if prompt_path.exists() else "You are a GitHub assistant."
    response = github_agent_llm.invoke([SystemMessage(content=prompt)] + list(state["messages"]))
    logger.info(f"GitHub agent response tool_calls: {getattr(response, 'tool_calls', [])}")
    return {"messages": [response]}

def comms_agent_call(state: AgentState):
    prompt_path = Path('config/comms_systemmessage.md')
    prompt = prompt_path.read_text(encoding='utf-8') if prompt_path.exists() else "You are a PlanetIX communications assistant."
    response = comms_agent_llm.invoke([SystemMessage(content=prompt)] + list(state["messages"]))
    return {"messages": [response]}

# --- SUPERVISOR WITH STRUCTURED OUTPUT ---
def supervisor(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]
    
    if not isinstance(last_message, HumanMessage):
        return {"next": "__end__"}
    
    # Handle content safely for Pylance (str or list)
    query_content = last_message.content
    if isinstance(query_content, list):
        query = " ".join([str(item.get("text", item)) if isinstance(item, dict) else str(item) for item in query_content])
    else:
        query = str(query_content)
    
    # Load supervisor system message
    sys_path = Path('config/supervisor_systemmessage.md')
    supervisor_sys = sys_path.read_text(encoding='utf-8') if sys_path.exists() else "Route the query to the correct agent."

    try:
        # Invoke xAI with structured output requirement
        response = cast(RouterResponse, structured_supervisor.invoke([
            SystemMessage(content=supervisor_sys),
            HumanMessage(content=f"User query: {query}")
        ]))
        
        next_node = response.next_node
        reason = response.reason
    except Exception as e:
        logger.error(f"Supervisor failed: {e}")
        next_node = "ambiguous"
        reason = f"Classification error: {str(e)}"

    logger.info(f"Supervisor routing to {next_node} (Reason: {reason})")
    
    return {"next": next_node}

# Graph construction
graph = StateGraph(AgentState)
graph.add_node("supervisor", supervisor)
graph.add_node("github_agent", github_agent_call)
graph.add_node("github_agent_tools", github_agent_tool_exec)
graph.add_node("comms_agent", comms_agent_call)
graph.add_node("comms_agent_tools", comms_agent_tool_exec)

# Start as supervisor 
graph.set_entry_point("supervisor")

# Supervisor routing based on state["next"]
graph.add_conditional_edges(
    "supervisor",
    lambda state: state["next"],
    {
        "github_agent": "github_agent", 
        "comms_agent": "comms_agent", 
        "ambiguous": END,
        "__end__": END
    }
)

# Helper function for agent tool loops
def should_continue(state: AgentState):
    last_msg = state["messages"][-1]
    if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
        return "tools"
    return "supervisor"

# Agent loops
graph.add_conditional_edges("github_agent", should_continue, {"tools": "github_agent_tools", "supervisor": "supervisor"})
graph.add_edge("github_agent_tools", "github_agent")

graph.add_conditional_edges("comms_agent", should_continue, {"tools": "comms_agent_tools", "supervisor": "supervisor"})
graph.add_edge("comms_agent_tools", "comms_agent")

# Compile the graph
app = graph.compile(checkpointer=InMemorySaver())
