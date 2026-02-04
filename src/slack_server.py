import os
import sys
import re
from pathlib import Path
from typing import cast
from dotenv import load_dotenv

# 1. SETUP PATHS AND ENVIRONMENT
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)

# 2. IMPORTS
import ngrok
from flask import Flask, request, make_response
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from langchain_core.runnables import RunnableConfig

# Import your agent logic
from agent import app as langgraph_app

# 3. SETUP SLACK BOLT
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
)
handler = SlackRequestHandler(app)

# 4. SHARED MESSAGE LOGIC
def process_message(event, say):
    raw_text = event.get("text", "")
    user_query = re.sub(r'<@U[A-Z0-9]+>', '', raw_text).strip()
    thread_ts = event.get("thread_ts", event["ts"])
    config = cast(RunnableConfig, {"configurable": {"thread_id": f"slack_{thread_ts}"}})
    
    try:
        result = langgraph_app.invoke({"messages": [("human", user_query)]}, config=config)
        response_text = result["messages"][-1].content
        say(text=response_text, thread_ts=thread_ts)
    except Exception as e:
        say(text=f"Agent Error: {str(e)}", thread_ts=thread_ts)

# 5. SLACK EVENT HANDLERS
@app.event("app_mention")
def handle_mentions(event, say):
    process_message(event, say)

# 6. FLASK SETUP WITH NGROK BYPASS
flask_app = Flask(__name__)

@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    # 1. Kolla om det är en URL-verifiering (Challenge)
    # Görs manuellt för att garantera svar inom 3 sekunder
    data = request.json
    if data and data.get("type") == "url_verification":
        print("DEBUG: Responding to Slack Challenge...")
        challenge_answer = make_response(data.get("challenge"), 200)
        challenge_answer.headers["Content-Type"] = "text/plain"
        challenge_answer.headers["ngrok-skip-browser-warning"] = "true"
        return challenge_answer

    # 2. Om det inte är en challenge, låt Bolt hantera det (Mentions etc.)
    print("DEBUG: Slack sent an event (Mention/Message)!")
    bolt_response = handler.handle(request)
    
    # Skapa Flask-svar från Bolt
    response = make_response(bolt_response.get_data(), bolt_response.status)
    for key, value in bolt_response.headers.items():
        response.headers[key] = value
    
    response.headers["ngrok-skip-browser-warning"] = "true"
    return response


@flask_app.route("/", methods=["GET"])
def health_check():
    print("DEBUG: Remote URL (Root) was accessed!") # Updated name
    response = make_response("🚀 Stack von Overflow's bridge is ONLINE!", 200)
    response.headers["ngrok-skip-browser-warning"] = "true"
    return response

# 7. AUTOMATIC NGROK TUNNEL
def start_ngrok():
    token = os.environ.get("NGROK_AUTHTOKEN")
    domain = os.environ.get("NGROK_DOMAIN")
    
    if not token or not domain:
        print("❌ Error: NGROK_AUTHTOKEN or NGROK_DOMAIN missing in .env")
        return

    try:
        listener = ngrok.forward(addr=3000, authtoken=token, domain=domain)
        print(f"✅ Tunnel ready: {listener.url()} -> localhost:3000")
    except Exception as e:
        print(f"❌ Failed to start ngrok: {e}")

# 8. MAIN EXECUTION
if __name__ == "__main__":
    start_ngrok()
    print("🚀 Slack Dispatcher is starting on port 3000...")
    # flask_app.run(port=3000)
flask_app.run(port=3000, debug=True, use_reloader=False)
