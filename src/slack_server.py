import os
import sys
import re
import traceback
import logging
from pathlib import Path
from typing import cast
from dotenv import load_dotenv
from flask import Flask, request, make_response
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from langchain_core.runnables import RunnableConfig

# Formatting and Styling
from slackstyler import SlackStyler

# 1. SETUP PATHS AND ENVIRONMENT
project_root = Path.cwd()
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)

signing_secret = os.environ.get("SLACK_SIGNING_SECRET")
bot_token = os.environ.get("SLACK_BOT_TOKEN")

if not signing_secret or not bot_token:
    print(f"❌ ERROR: Credentials missing in {env_path}")
    sys.exit(1)

# 2. INITIALIZE LANGGRAPH AGENT
langgraph_app = None
try:
    # Import the compiled graph from your agent.py
    from agent import app as imported_app
    langgraph_app = imported_app
    print("✅ LangGraph Agent loaded successfully.")
except Exception as e:
    print(f"❌ Failed to load agent.py: {e}")

# 3. SETUP SLACK BOLT
# We pass the token and secret to initialize the Bolt app
app = App(token=bot_token, signing_secret=signing_secret)
handler = SlackRequestHandler(app)

# 4. SHARED MESSAGE LOGIC
def process_message(event, client, say):
    """
    Core logic to handle incoming messages.
    Uses an initial 'Thinking' message that gets updated once the AI finishes.
    """
    if langgraph_app is None:
        say(text="⚠️ System Error: AI Engine is offline.", thread_ts=event.get("ts"))
        return

    # Use thread_ts if available (replies in thread), otherwise use message ts
    thread_ts = event.get("thread_ts", event["ts"])
    channel_id = event["channel"]

    try:
        # Step A: Post an initial 'Thinking' message to give immediate feedback
        # This prevents Slack from showing a 'dispatch failed' error if the AI is slow
        initial_res = client.chat_postMessage(
            channel=channel_id,
            text="_Thinking..._ 🧠",
            thread_ts=thread_ts
        )
        thinking_msg_ts = initial_res["ts"]

        # Step B: Prepare the input for the agent
        raw_text = event.get("text", "")
        # Remove the @bot mention from the query string
        user_query = re.sub(r'<@U[A-Z0-9]+>', '', raw_text).strip()
        
        # Configure LangGraph thread context
        config = cast(RunnableConfig, {"configurable": {"thread_id": f"slack_{thread_ts}"}})
        
        print(f"🤖 Agent processing: '{user_query}'")
        
        # Step C: Invoke the LangGraph (Running on CPU - might take a few seconds)
        result = langgraph_app.invoke({"messages": [("human", user_query)]}, config=config)
        
        # Step D: Extract content and format it for Slack
        raw_response = result["messages"][-1].content
        styler = SlackStyler()
        formatted_text = styler.convert(raw_response)
        
        # Step E: Update the initial 'Thinking' message with the actual AI response
        client.chat_update(
            channel=channel_id,
            ts=thinking_msg_ts,
            text=formatted_text
        )
        print("✅ Response updated and sent successfully.")

    except Exception as e:
        print(f"❌ Error in process_message: {str(e)}")
        traceback.print_exc()
        # Fallback: Tell the user something went wrong
        say(text=f"⚠️ Agent Error: {str(e)}", thread_ts=thread_ts)

# 5. SLACK EVENT HANDLERS
@app.event("app_mention")
def handle_mentions(event, client, say):
    """Triggered when the bot is @mentioned in a channel."""
    process_message(event, client, say)

@app.message(re.compile(".*"))
def handle_direct_messages(event, client, say):
    """Triggered for all Direct Messages to the bot."""
    if event.get("channel_type") == "im":
        process_message(event, client, say)

# 6. FLASK ROUTING
flask_app = Flask(__name__)

@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    """
    Standard Slack event endpoint. 
    Bolt's handler manages signature verification and URL challenges.
    """
    bolt_response = handler.handle(request)
    
    # Inject ngrok bypass header for free-tier compatibility
    response = make_response(bolt_response.get_data(), bolt_response.status)
    for key, value in bolt_response.headers.items():
        response.headers[key] = value
    response.headers["ngrok-skip-browser-warning"] = "true"
    
    return response

@flask_app.route("/", methods=["GET"])
def health_check():
    """Simple GET route to check if the server is up."""
    return "🚀 Slack Bridge is ONLINE!", 200

# 7. AUTOMATIC NGROK TUNNEL
def start_ngrok():
    """Start ngrok tunnel using the official Python SDK."""
    token = os.environ.get("NGROK_AUTHTOKEN")
    domain = os.environ.get("NGROK_DOMAIN")
    if not token or not domain:
        print("⚠️ Skipping ngrok: NGROK_AUTHTOKEN or NGROK_DOMAIN missing.")
        return
    try:
        import ngrok
        listener = ngrok.forward(addr=3000, authtoken=token, domain=domain)
        print(f"✅ Tunnel ready: {listener.url()} -> localhost:3000")
    except Exception as e:
        print(f"❌ Ngrok startup failed: {e}")

# 8. STARTUP
if __name__ == "__main__":
    # Log level INFO ensures we see incoming requests in terminal
    logging.basicConfig(level=logging.INFO)
    start_ngrok()
    print("🚀 Server starting on port 3000...")
    # use_reloader=False is required when running ngrok inside the script
    flask_app.run(port=3000, host='0.0.0.0', debug=True, use_reloader=False)
