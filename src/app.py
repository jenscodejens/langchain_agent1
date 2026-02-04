import os
import sys
import logging
import json
import asyncio
from datetime import datetime, timezone
from typing import cast

# Ensure backend/agent can be found
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import chainlit as cl
from agent import app as langgraph_app
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

# Maps LangGraph node names to user-friendly display names in Chainlit
AGENT_NAMES = {
    "github_agent": "GitHub Agent",
    "comms_agent": "PlanetIX Dispatch",
    "supervisor": "The Boss",
    "ambiguous": "Confused Agent"
}

# --- UTILS ---
log_lock = asyncio.Lock()
LOG_FILE_PATH = os.path.join(os.path.dirname(__file__), '..', 'logs', 'conversation_history.log')

def serializable_dict(obj):
    """Recursively converts LangChain messages to serializable dicts for JSON logging."""
    if hasattr(obj, "to_json"):
        return obj.to_json()
    if hasattr(obj, "dict"):
        return obj.dict()
    return str(obj)

async def log_to_file(message: str):
    """Asynchronously log a message to the conversation history file with a timestamp."""
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] {message}\n"
    async with log_lock:
        os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)
        with open(LOG_FILE_PATH, 'a', encoding='utf-8') as f:
            f.write(log_entry)

previous_thread_id = None

# --- CHAINLIT EVENTS ---

@cl.on_stop
async def on_session_stop():
    """Triggered when the user session ends or the chat is closed."""
    await log_to_file("=== Conversation End ===")

@cl.on_message
async def main(message: cl.Message):
    """Handle incoming user messages and stream responses from the LangGraph agent."""
    global previous_thread_id
    
    # Configuration for LangGraph (manages conversation memory)
    config = cast(RunnableConfig, {
        "configurable": {"thread_id": cl.user_session.get("thread_id", "default")}
    })
    
    current_thread_id = config.get("configurable", {}).get("thread_id", "default")
    
    # New thread detection for logging
    if previous_thread_id and previous_thread_id != current_thread_id:
        await log_to_file("=== Conversation End ===")
    previous_thread_id = current_thread_id

    await log_to_file(f"Human: {message.content}")

    # Input preparation
    inputs = {"messages": [HumanMessage(content=message.content)]}
    ai_msg = None
    tool_steps = {}
    total_tokens = cl.user_session.get("total_tokens", 0)
    message_tokens = 0
    ai_response_buffer = []
    
    # Default name before any node is identified
    current_agent_name = "Supervisor"

    # Stream LangGraph events
    async for event in langgraph_app.astream_events(inputs, config=config, version="v2"):
        kind = event["event"]

        # DYNAMIC AGENT IDENTIFICATION
        # We extract which node is currently running to update the 'author' in the UI
        node_name = event.get("metadata", {}).get("langgraph_node")
        if node_name in AGENT_NAMES:
            current_agent_name = AGENT_NAMES[node_name]

        # TOOL EXECUTION START
        if kind == "on_tool_start":
            tool_name = event.get("name", "Tool")
            tool_input = event["data"].get("input")
            run_id = event["run_id"]

            await log_to_file(f"Tool Call: {tool_name} - Input: {json.dumps(tool_input)}")

            # Create an expandable UI element for the tool execution
            step = cl.Step(name=f"{tool_name} Execution", type="tool")
            await step.send()
            tool_steps[run_id] = step

        # TOOL EXECUTION END
        elif kind == "on_tool_end":
            run_id = event["run_id"]
            if run_id in tool_steps:
                step = tool_steps[run_id]
                tool_output = event["data"].get("output")
                await log_to_file(f"Execution result: {tool_output}")

                # Safely serialize metadata for display
                safe_data = json.dumps(event["data"], default=serializable_dict, indent=2)

                details = cl.Text(
                    name="Response & Metadata",
                    content=f"### Tool Response\n{tool_output}\n\n### Full Metadata\n```json\n{safe_data}\n```",
                    display="inline"
                )

                step.elements = [details]
                step.output = "Tool execution completed."
                await step.update()

        # CHAT MODEL STREAMING (Real-time response)
        elif kind == "on_chat_model_stream":
            chunk = event["data"].get("chunk")
            if chunk and hasattr(chunk, 'content') and chunk.content:
                ai_response_buffer.append(chunk.content)
                
                # Initialize the message if it doesn't exist
                if not ai_msg:
                    # 'author' is set dynamically based on current_agent_name
                    ai_msg = cl.Message(content="", author=current_agent_name)
                    await ai_msg.send()
                
                # Update author if the agent switched mid-stream
                if ai_msg.author != current_agent_name:
                    ai_msg.author = current_agent_name
                
                await ai_msg.stream_token(chunk.content)

        # CHAT MODEL END (Finalizing node execution)
        elif kind == "on_chat_model_end":
            full_ai_response = ''.join(ai_response_buffer)
            await log_to_file(f"AI ({current_agent_name}): {full_ai_response}")
            ai_response_buffer.clear() 

            # Handle token usage accounting
            output = event["data"].get("output")
            if output and hasattr(output, 'usage_metadata') and output.usage_metadata:
                usage = output.usage_metadata
                tokens = usage.get("total_tokens", 0)
                message_tokens += tokens
                total_tokens += tokens
                cl.user_session.set("total_tokens", total_tokens)

    # 4. Finalize the AI message in the UI
    if ai_msg:
        await ai_msg.update()

    # 5. Token usage report (System message)
    if message_tokens > 0:
        await cl.Message(
            content=f"**Tokens used:** {message_tokens} | **Total session:** {total_tokens}", 
            author="System"
        ).send()

    # Save state reference
    cl.user_session.set("thread_id", config.get("configurable", {}).get("thread_id", "default"))
