import chainlit as cl
from agent import app as langgraph_app
from langchain_core.messages import HumanMessage
import json

def serializable_dict(obj):
    """Recursively converts LangChain messages to serializable dicts."""
    if hasattr(obj, "to_json"):
        return obj.to_json()
    if hasattr(obj, "dict"):
        return obj.dict()
    return str(obj)

@cl.on_message
async def main(message: cl.Message):
    config = {"configurable": {"thread_id": cl.user_session.get("thread_id", "default")}}
    inputs = {"messages": [HumanMessage(content=message.content)]}

    ai_msg = None
    tool_steps = {}
    total_tokens = cl.user_session.get("total_tokens", 0)
    
    async for event in langgraph_app.astream_events(inputs, config=config, version="v2"):
        kind = event["event"]

        if kind == "on_tool_start":
            tool_name = event.get("name", "Tool")
            tool_input = event["data"].get("input")
            run_id = event["run_id"]
            tokens_used = event["data"].get("tokens_used", "N/A")
            
            # Send basic info as a message (visible outside any expandable elements)
            await cl.Message(content=(
                f"**Tool:** {tool_name}\n"
                f"**Tool ID:** `{run_id}`\n"
                f"**Arguments:** `{json.dumps(tool_input)}`\n"
                f"**Tokens Used:** `{tokens_used}`"
            )).send()
            
            # Step for expandable details
            step = cl.Step(name=f"{tool_name} Execution", type="tool")
            await step.send()
            tool_steps[run_id] = step

        elif kind == "on_tool_end":
            run_id = event["run_id"]
            if run_id in tool_steps:
                step = tool_steps[run_id]
                tool_output = event["data"].get("output")
                
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
            chunk = event["data"]["chunk"]
            if hasattr(chunk, 'content') and chunk.content:
                if not ai_msg:
                    ai_msg = cl.Message(content="", author="assistant")
                    await ai_msg.send()
                await ai_msg.stream_token(chunk.content)

        elif kind == "on_chat_model_end":
            output = event["data"]["output"]
            if hasattr(output, 'usage_metadata'):
                usage = output.usage_metadata
                tokens = usage.get("total_tokens", 0)
                total_tokens += tokens
                cl.user_session.set("total_tokens", total_tokens)
                await cl.Message(content=f"**Tokens used in this response:** {tokens}\n**Total tokens so far:** {total_tokens}", author="system").send()

    # Ensure the final AI message is sent after streaming finishes
    if ai_msg:
        await ai_msg.send()

    cl.user_session.set("thread_id", config["configurable"]["thread_id"])
