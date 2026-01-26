import os
# os.environ["PYTHONIOENCODING"] = "utf-8"

from datetime import datetime
from langchain.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage, SystemMessage, AIMessage
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, END
from langchain_chroma import Chroma

from typing import Annotated, Sequence, TypedDict
from dotenv import load_dotenv
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper

import ddgs
import logging

from colorama import init, Fore, Style
init(autoreset=True)

load_dotenv()
logger = logging.getLogger(__name__)
ddg_api = DuckDuckGoSearchAPIWrapper(max_results=3)

from llm_config import embeddings, llm_model

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages] # provides the meta data

@tool("get_date_and_time", description="Returns the current date and time.") 
def current_datetime(_: str = "") -> str:
     """ Returns the current date and time in multiple formats. The LLM can choose which part to use. """ 
     now = datetime.now()
     return {
             "date": now.strftime("%Y-%m-%d"),
             "time": now.strftime("%H:%M"),
             "datetime": now.strftime("%Y-%m-%d %H:%M")
             }

# Used during development, slow tool. Excluded from tool list currently.
@tool("web_search", description="Performs a websearch using DuckDuckGo. The LLM can choose what is relevant and how much information the reply should consist of depending on the query. Use this tool whenever you:- Need up-to-date information (news, current events, recent papers, prices, stats), don't already know the answer from training data- Want to verify / fact-check something. Use quotes for exact phrases, -exclude, site:domain.com, etc. when it helps.")
def duckduckgo_web_search(query: str) -> str:
    """ Simple web search using DuckDuckGo """
    try:
        # Use the standard wrapper for cleaner result handling
        return ddg_api.run(query)
    except Exception as e:
        # Let the middleware handle the exception bubble-up
        raise RuntimeError(f"Search failed for query '{query}': {str(e)}")

@tool("retrieve_github_info", description="Retrieve relevant information from GitHub repositories stored in the RAG database. Use this for questions about code, repositories, or technical details from the configured GitHub repos. Show the code snippet(s) from where you base your response on")
def retrieve_github_info(query: str) -> str:
    """ Retrieve context from GitHub repos """
    try:
        vectorstore = Chroma(persist_directory="./chroma_db", embedding_function=embeddings, collection_name="github_repos")
        docs = vectorstore.similarity_search(query, k=5)
        context = "\n\n".join([f"Source: {doc.metadata.get('source', 'unknown')}\nLanguage: {doc.metadata.get('language', 'unknown')}\n{doc.page_content}" for doc in docs])
        return context
    except Exception as e:
        return f"Retrieval failed: {str(e)}"

@tool("summarize_text", description="Summarize long text content to make it more concise. Use this when retrieved information is too lengthy.")
def summarize_text(text: str) -> str:
    """ Summarize text using the LLM """
    try:
        prompt = f"Summarize the following text concisely:\n\n{text}"
        response = llm_model.invoke([SystemMessage(content="You are a summarization assistant."), HumanMessage(content=prompt)])
        return response.content
    except Exception as e:
        return f"Summarization failed: {str(e)}"

tools = [current_datetime, retrieve_github_info, summarize_text]
tool_dict = {tool.name: tool for tool in tools}

llm_model = llm_model.bind_tools(tools)

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

# Temperature set to 0 for the moment, add another llm config for non-github related questions in the future.


def model_call(state: AgentState) -> AgentState:
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

app = graph.compile(checkpointer=InMemorySaver())

config = {"configurable": {"thread_id": "conversation_1"}}
