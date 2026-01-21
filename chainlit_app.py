import chainlit as cl
from app import app as langgraph_app
from langchain_core.messages import HumanMessage, AIMessage

@cl.on_message
async def main(message: cl.Message):
    # Send user message to LangGraph
    config = {"configurable": {"thread_id": cl.user_session.get("thread_id", "default")}}

    inputs = {"messages": [HumanMessage(content=message.content)]}

    # Stream the response
    async for event in langgraph_app.astream(inputs, config=config):
        for node, messages in event.items():
            for msg in messages.get("messages", []):
                if hasattr(msg, 'content') and msg.content:
                    await cl.Message(content=msg.content).send()
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    for tool_call in msg.tool_calls:
                        tool_msg = f"Tool Call: {tool_call['name']} with args {tool_call['args']}"
                        await cl.Message(content=tool_msg).send()
                # For tool messages, display content
                #if hasattr(msg, 'tool_call_id'):
                #    await cl.Message(content=f"Tool Result: {msg.content}").send()

    # Update thread_id
    cl.user_session.set("thread_id", config["configurable"]["thread_id"])