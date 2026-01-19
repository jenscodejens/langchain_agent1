import os
os.environ["PYTHONIOENCODING"] = "utf-8"

from datetime import datetime
from langchain_xai import ChatXAI
from langchain_openai import OpenAIEmbeddings
from langchain.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents.middleware import SummarizationMiddleware
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage, SystemMessage, AIMessage
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, END

from typing import Annotated, Sequence, TypedDict
from dotenv import load_dotenv
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper

import logging

from colorama import init, Fore, Style
init(autoreset=True)

load_dotenv()
logger = logging.getLogger(__name__)
ddg_api = DuckDuckGoSearchAPIWrapper(max_results=3)

# LM Studio's running bge-m3 embedding model
embeddings = OpenAIEmbeddings(
    model="bge-m3", 
    openai_api_key="not-needed",
    openai_api_base="http://localhost:1234/v1" 
)


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

@tool("web_search", description="Performs a websearch using DuckDuckGo. The LLM can choose what is relevant and how much information the reply should consist of depending on the query. Use this tool whenever you:- Need up-to-date information (news, current events, recent papers, prices, stats), don't already know the answer from training data- Want to verify / fact-check something. Use quotes for exact phrases, -exclude, site:domain.com, etc. when it helps.")
def duckduckgo_web_search(query: str) -> str:
    """ Simple web search using DuckDuckGo """
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
    temperature=0.3,
    timeout=25,
    verbose=True
).bind_tools(tools)


def model_call(state:AgentState) -> AgentState:
    system_prompt = SystemMessage(content=
        "You are a helpful AI assistant. Please answer my query to the best of your ability. If you don't know the answer, ask for more context if needed. Use emojis only when it is suitable. Check the conversation history for recent date/time tool results. If the information is still current (e.g., within the same minute), reuse it instead of calling the tool again. Consider conversation history when deciding relevance also pay attention to words of a time-sensetive nature."
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

app = graph.compile(checkpointer=InMemorySaver())

def print_stream(stream):
    for s in stream:
        for node_output in s.values():
            for message in node_output.get("messages", []):
                if isinstance(message, HumanMessage):
                    print(Fore.GREEN + "[Human Message]\t" + message.content + Style.RESET_ALL)
                elif isinstance(message, AIMessage):
                    if message.tool_calls:
                        for tool_call in message.tool_calls:
                            print(
                                Fore.WHITE +
                                "[Invoke Tool]\n"
                                f"     Tool: {Fore.BLUE}{tool_call['name']}{Fore.WHITE}\n"
                                f"     Call ID: {tool_call['id']}\n"
                                f"     Args:\n"
                                f"     {tool_call['args']}" +
                                Style.RESET_ALL
                            )
                    if message.content:  # Only print if there's actual content
                        print(Fore.YELLOW + "[AI Message]\t" + message.content + Style.RESET_ALL)
                elif isinstance(message, ToolMessage):
                    print(Fore.BLUE + "[Tool Message]\t" + message.content + Style.RESET_ALL)
                else:
                    print(message.content)  # Fallback

human_messages = [
    # HumanMessage(content="what is my name"),
    HumanMessage(content="my name is Jens what date and time is it"),
    HumanMessage(content="what date is it"),
    #HumanMessage(content="what time is it"),
    #HumanMessage(content="what is my name"),
    #HumanMessage(content="how did Minnesota Vikings perform in the NFL 2021?"),
    HumanMessage(content="What is my name and did the Minnesota Vikings qualify for playoffs 2025/2026 season?"),
    HumanMessage(content="what is the temperature in Stockholm?"),
]

config = {"configurable": {"thread_id": "conversation_1"}}
for msg in human_messages:
    print(Fore.GREEN + "[Human Message]\t" + msg.content + Style.RESET_ALL)
    inputs = {"messages": [msg]}
    print_stream(app.stream(inputs, config=config, stream_mode="updates"))