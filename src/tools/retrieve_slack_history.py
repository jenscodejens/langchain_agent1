import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from langchain.tools import tool
from dotenv import load_dotenv

load_dotenv()

@tool("retrieve_slack_history", description="Fetches the latest messages from a specific Slack channel. Use this to summarize recent discussions, check for community questions, or stay updated on Slack activity.")
def retrieve_slack_history(limit: int = 20) -> str:
    """Fetches recent history from the Slack channel ai-bot-tester."""
    client = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"))
    channel_id = "C0ABRUY7VSP" # Your specific channel
    
    try:
        # Fetch history using the token's 'channels:history' scope
        response = client.conversations_history(channel=channel_id, limit=limit)
        messages = response["messages"]
        
        if not messages:
            return "The channel history is empty."
            
        # Format the messages into a readable string for the Agent
        formatted_history = []
        for msg in reversed(messages):
            user = msg.get("user", "Unknown User")
            text = msg.get("text", "")
            ts = msg.get("ts", "")
            formatted_history.append(f"[{ts}] User {user}: {text}")
            
        return "\n".join(formatted_history)
        
    except SlackApiError as e:
        return f"Error fetching Slack history: {e.response['error']}"
