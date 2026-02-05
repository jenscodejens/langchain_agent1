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

# 1. SETUP PATHS AND ENVIRONMENT
# We assume you run from 'langchain_agent1' root
project_root = Path.cwd()
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)

# Verification of credentials
signing_secret = os.environ.get("SLACK_SIGNING_SECRET")
bot_token = os.environ.get("SLACK_BOT_TOKEN")

if not signing_secret or not bot_token:
    print(f"❌ ERROR: Credentials missing in {env_path}")
    print(f"Check if SLACK_SIGNING_SECRET and SLACK_BOT_TOKEN exist.")
    sys.exit(1)
else:
    print(f"✅ Credentials loaded. Secret starts with: {signing_secret[:4]}...")

# 2. INITIALIZE LANGGRAPH AGENT
langgraph_app = None
try:
    # This will now look in both / and /src/ for agent.py
    from agent import app as imported_app
    langgraph_app = imported_app
    print("✅ LangGraph Agent loaded successfully.")
except Exception as e:
    print(f"❌ Failed to load agent.py: {e}")

# 3. SETUP SLACK BOLT
app = App(token=bot_token, signing_secret=signing_secret)
handler = SlackRequestHandler(app)

# 4. SHARED MESSAGE LOGIC
def process_message(event, say):
    """Handles logic for both mentions and DMs."""
    if langgraph_app is None:
        say(text="⚠️ System Error: AI Engine is offline.", thread_ts=event.get("ts"))
        return

    try:
        raw_text = event.get("text", "")
        # Remove @Bot mentions from the text
        user_query = re.sub(r'<@U[A-Z0-9]+>', '', raw_text).strip()
        
        # Keep conversation thread consistency
        thread_ts = event.get("thread_ts", event["ts"])
        config = cast(RunnableConfig, {"configurable": {"thread_id": f"slack_{thread_ts}"}})
        
        print(f"🤖 Agent processing: '{user_query}'")
        result = langgraph_app.invoke({"messages": [("human", user_query)]}, config=config)
        
        response_text = result["messages"][-1].content
        say(text=response_text, thread_ts=thread_ts)
        print("✅ Response sent.")

    except Exception as e:
        print(f"❌ Error in process_message: {str(e)}")
        traceback.print_exc()
        say(text=f"⚠️ Agent Error: {str(e)}", thread_ts=event.get("ts"))

# 5. SLACK EVENT HANDLERS
@app.event("app_mention")
def handle_mentions(event, say):
    """Triggered when the bot is @mentioned in a channel."""
    process_message(event, say)

@app.message(re.compile(".*"))
def handle_direct_messages(event, say):
    """Triggered for all Direct Messages to the bot."""
    process_message(event, say)

# 6. FLASK ROUTING
flask_app = Flask(__name__)

@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    """
    Standard Slack event endpoint. 
    Bolt's handler.handle(request) automatically manages 
    signature verification and URL challenges.
    """
    return handler.handle(request)

@flask_app.route("/", methods=["GET"])
def health_check():
    """Simple GET route to check if the server is up."""
    return "🚀 Slack Bridge is ONLINE!", 200

# 7. AUTOMATIC NGROK TUNNEL
def start_ngrok():
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
    # Log level INFO ensures we see incoming requests
    logging.basicConfig(level=logging.INFO)
    start_ngrok()
    print("🚀 Server starting on port 3000...")
    # use_reloader=False prevents ngrok from trying to open two tunnels
    flask_app.run(port=3000, host='0.0.0.0', debug=True, use_reloader=False)
