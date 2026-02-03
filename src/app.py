import os
# os.environ['TQDM_DISABLE'] = '1'  # Disable tqdm progress bars

import logging

# Suppress verbose INFO logs from libraries in terminal output
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('chromadb').setLevel(logging.WARNING)
logging.getLogger('chromadb.telemetry.product.posthog').setLevel(logging.WARNING)
logging.getLogger('transformers').setLevel(logging.WARNING)
logging.getLogger('sentence_transformers').setLevel(logging.WARNING)

import chainlit as cl
from .agent import app as langgraph_app
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
import json
import asyncio
from datetime import datetime, timezone
from typing import cast

log_lock = asyncio.Lock()

def serializable_dict(obj):
    """Recursively converts LangChain messages to serializable dicts."""
    if hasattr(obj, "to_json"):
        return obj.to_json()
    if hasattr(obj, "dict"):
        return obj.dict()
    return str(obj)

LOG_FILE_PATH = os.path.join(os.path.dirname(__file__), '..', 'logs', 'conversation_history.log')

async def log_to_file(message: str):
    """Asynchronously log a message to the conversation history file."""
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')  # YYYY-MM-DD HH:MM:SS format
    log_entry = f"[{timestamp}] {message}\n"
    async with log_lock:  # Prevent concurrent writes
        with open(LOG_FILE_PATH, 'a', encoding='utf-8') as f:
            f.write(log_entry)

previous_thread_id = None

@cl.on_stop
async def on_session_stop():
    await log_to_file("=== Conversation End ===")

@cl.on_message
async def main(message: cl.Message):
    """Handle incoming messages and process them through the LangGraph app."""
    global previous_thread_id
    config = cast(RunnableConfig, {"configurable": {"thread_id": cl.user_session.get("thread_id", "default")}})
    current_thread_id = config.get("configurable", {}).get("thread_id", "default")
    if previous_thread_id and previous_thread_id != current_thread_id:
        await log_to_file("=== Conversation End ===")
    previous_thread_id = current_thread_id

    await log_to_file(f"Human: {message.content}")

    inputs = {"messages": [HumanMessage(content=message.content)]}

    ai_msg = None
    tool_steps = {}
    total_tokens = cl.user_session.get("total_tokens", 0)
    message_tokens = 0
    ai_response_buffer = []
    
    async for event in langgraph_app.astream_events(inputs, config=config, version="v2"):
        kind = event["event"]

        if kind == "on_tool_start":
            tool_name = event.get("name", "Tool")
            tool_input = event["data"].get("input")
            run_id = event["run_id"]
            tokens_used = event["data"].get("tokens_used", "N/A")

            await log_to_file(f"Tool Call: {tool_name} - Input: {json.dumps(tool_input)}")

            # Send basic info as a message (visible outside any expandable elements)
            # await cl.Message(content=(
            #     f"**Tool:** {tool_name}\n"
            #     f"**Tool ID:** `{run_id}`\n"
            #     f"**Arguments:** `{json.dumps(tool_input)}`\n"
            #     f"**Tokens Used:** `{tokens_used}`"
            # ), author="Tools").send()

            # Step for expandable details
            step = cl.Step(name=f"{tool_name} Execution", type="tool")
            await step.send()
            tool_steps[run_id] = step

        elif kind == "on_tool_end":
            run_id = event["run_id"]
            if run_id in tool_steps:
                step = tool_steps[run_id]
                tool_output = event["data"].get("output")

                await log_to_file(f"Execution result: {tool_output}")

                # Metadata extraction with safe serialization
                # Use .dict() or string conversion to avoid TypeError
                safe_data = json.dumps(event["data"], default=serializable_dict, indent=2)

                # Place content and metadata INSIDE expandable element
                details = cl.Text(
                    name="Response & Metadata",
                    content=f"### Tool Response\n{tool_output}\n\n### Full Metadata\n```json\n{safe_data}\n```",
                    display="inline" # Inline in a step creates an expandable element
                )

                step.elements = [details]
                step.output = "Tool execution completed."
                await step.update()

        elif kind == "on_chat_model_stream":
            chunk = event["data"].get("chunk")
            if chunk and hasattr(chunk, 'content') and chunk.content:
                ai_response_buffer.append(chunk.content)
                if not ai_msg:
                    ai_msg = cl.Message(content="", author="assistant")
                    await ai_msg.send()
                await ai_msg.stream_token(chunk.content)

        elif kind == "on_chat_model_end":
            full_ai_response = ''.join(ai_response_buffer)
            await log_to_file(f"AI: {full_ai_response}")
            ai_response_buffer.clear()  # Reset for next message

            output = event["data"].get("output")
            if output and hasattr(output, 'usage_metadata') and output.usage_metadata is not None and hasattr(output.usage_metadata, 'get'):
                usage = output.usage_metadata
                tokens = usage.get("total_tokens", 0)
                message_tokens += tokens
                total_tokens += tokens
                cl.user_session.set("total_tokens", total_tokens)

    # Ensure the final AI message is sent after streaming finishes
    if ai_msg:
        await ai_msg.send()

    if message_tokens > 0:
        await cl.Message(content=f"**Tokens used in this response:** {message_tokens}\n**Total tokens so far:** {total_tokens}", author="system").send()

    cl.user_session.set("thread_id", config.get("configurable", {}).get("thread_id", "default"))
