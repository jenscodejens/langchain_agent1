import os
import sys
import re
import traceback
from pathlib import Path
from typing import cast
from dotenv import load_dotenv

# 1. SETUP PATHS AND ENVIRONMENT
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load .env explicitly
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)

# 2. NOW IMPORT THE REST
import ngrok
from flask import Flask, request, make_response
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from langchain_core.runnables import RunnableConfig

# Initialize as None to satisfy scope, but try to import
langgraph_app = None
try:
    from agent import app as imported_app
    langgraph_app = imported_app
    print("✅ LangGraph Agent loaded successfully.")
except Exception as e:
    print(f"❌ Failed to load agent.py: {e}")
    traceback.print_exc()

# 3. SETUP SLACK BOLT
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
)
handler = SlackRequestHandler(app)

# 4. SHARED MESSAGE LOGIC WITH DEEP DEBUG
def process_message(event, say):
    """Central logic with type guarding for Pylance."""
    # Guard Clause: This tells Pylance that langgraph_app cannot be None beyond this point
    if langgraph_app is None:
        print("❌ ERROR: langgraph_app is not initialized.")
        say(text="⚠️ System Error: AI Engine is offline.", thread_ts=event.get("ts"))
        return

    try:
        raw_text = event.get("text", "")
        user_query = re.sub(r'<@U[A-Z0-9]+>', '', raw_text).strip()
        
        print(f"DEBUG: Input received: '{user_query}'")
        thread_ts = event.get("thread_ts", event["ts"])
        config = cast(RunnableConfig, {"configurable": {"thread_id": f"slack_{thread_ts}"}})
        
        print("DEBUG: Executing LangGraph.invoke()...")
        
        # Pylance is now happy because of the 'is None' check above
        result = langgraph_app.invoke({"messages": [("human", user_query)]}, config=config)
        
        response_text = result["messages"][-1].content
        say(text=response_text, thread_ts=thread_ts)
        print("✅ Response sent successfully.")

    except Exception as e:
        print(f"❌ ERROR in process_message: {str(e)}")
        traceback.print_exc()
        say(text=f"⚠️ Agent Error: {str(e)}", thread_ts=event.get("ts"))

# 5. SLACK EVENT HANDLERS
@app.event("app_mention")
def handle_mentions(event, say):
    process_message(event, say)

# 6. FLASK SETUP WITH CHALLENGE BYPASS
flask_app = Flask(__name__)

@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    data = request.json
    if data and data.get("type") == "url_verification":
        challenge_answer = make_response(data.get("challenge"), 200)
        challenge_answer.headers["Content-Type"] = "text/plain"
        challenge_answer.headers["ngrok-skip-browser-warning"] = "true"
        return challenge_answer

    bolt_response = handler.handle(request)
    response = make_response(bolt_response.get_data(), bolt_response.status)
    for key, value in bolt_response.headers.items():
        response.headers[key] = value
    response.headers["ngrok-skip-browser-warning"] = "true"
    return response

@flask_app.route("/", methods=["GET"])
def health_check():
    response = make_response("🚀 Stack von Overflow's bridge is ONLINE!", 200)
    response.headers["ngrok-skip-browser-warning"] = "true"
    return response

# 7. AUTOMATIC NGROK TUNNEL
def start_ngrok():
    token = os.environ.get("NGROK_AUTHTOKEN")
    domain = os.environ.get("NGROK_DOMAIN")
    if not token or not domain:
        print("❌ Error: Missing NGROK config in .env")
        return
    try:
        listener = ngrok.forward(addr=3000, authtoken=token, domain=domain)
        print(f"✅ Tunnel ready: {listener.url()} -> localhost:3000")
    except Exception as e:
        print(f"❌ Failed to start ngrok: {e}")

if __name__ == "__main__":
    import logging
    # Tvinga loggning till INFO-nivå så vi ser alla POST-anrop
    logging.basicConfig(level=logging.INFO)
    
    start_ngrok()
    print("🚀 Slack Dispatcher is starting...", flush=True)
    flask_app.run(port=3000, host='0.0.0.0', debug=True, use_reloader=False)
