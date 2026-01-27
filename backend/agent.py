from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage, SystemMessage, AIMessage
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, END

from typing import Annotated, Sequence, TypedDict
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

from config.llm_config import embeddings, llm_model
from tools import all_tools, tool_dict

class AgentState(TypedDict):
    """State for the agent graph, containing messages."""
    messages: Annotated[Sequence[BaseMessage], add_messages] # provides the meta data

llm_model = llm_model.bind_tools(all_tools)

def custom_tool_executor(state: AgentState) -> AgentState:
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

# Temperature set to 0 for the moment, add another llm config for non-github related questions in the future.


def model_call(state: AgentState) -> AgentState:
    """Call the LLM model with system prompt and messages."""
    system_prompt = SystemMessage(content="""You are a specialized GitHub Repository Assistant. Your primary goal is to provide technical insights and information based on the documents in your RAG vector database.

**Operating Guidelines:**
1. **Tool Usage:** Always use the `retrieve_github_info` tool first for queries regarding repositories, codebases, or technical documentation.
2. **Conciseness:** If the retrieved data is long or dense, apply the `summarize_text` tool to provide a clear, high-level overview.
3. **Context Awareness:** Incorporate conversation history and prioritize time-sensitive data (especially relevant for 2026 data). 
4. **Uncertainty:** If the database does not contain the answer, explicitly state what information is missing and ask for specific context.
5. **Tone & Style:** Maintain a professional, helpful tone. Use emojis sparingly and only when they enhance the developer-centric context. 🛠️""")
    
    response = llm_model.invoke([system_prompt] + state["messages"])
    return {"messages": [response]}

def should_iterate(state: AgentState):
    """Determine if the graph should iterate or end."""
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

# The actual initialization of the agent
app = graph.compile(checkpointer=InMemorySaver())

config = {"configurable": {"thread_id": "conversation_1"}}
