import chainlit as cl
from app import app as langgraph_app
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

@cl.on_message
async def main(message: cl.Message):
    config = {"configurable": {"thread_id": cl.user_session.get("thread_id", "default")}}
    inputs = {"messages": [HumanMessage(content=message.content)]}
    
    ai_msg = None
    
    async for event in langgraph_app.astream_events(inputs, config=config, version="v2"):
        if event["event"] == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            if chunk.content:
                if not ai_msg:
                    ai_msg = cl.Message(content="")
                    await ai_msg.send()
                ai_msg.content += chunk.content
                await ai_msg.update()
        elif event["event"] == "on_chat_model_end":
            # Handle tool calls if present in the final message
            final_msg = event["data"]["output"]
            if hasattr(final_msg, 'tool_calls') and final_msg.tool_calls and ai_msg:
                tool_text = "\n\nTool Calls:\n" + "\n".join([
                    f"- {tc['name']}: {tc['args']}" for tc in final_msg.tool_calls
                ])
                ai_msg.content += tool_text
                await ai_msg.update()
        elif event["event"] == "on_tool_end":
            tool_output = event["data"]["output"]
            tool_msg = cl.Message(content=f"**Tool Result:** {tool_output}")
            await tool_msg.send()
    
    cl.user_session.set("thread_id", config["configurable"]["thread_id"])