# Usage Guide & Examples

## Chainlit UI
1. Run `python src/run_chainlit.py`.
2. Open `http://localhost:8000`.
3. Chat:

### GitHub Examples
```
User: What's in the langchain_agent1 repo?
Supervisor → GitHub Agent → retrieve_github_info → "Overview of files..."

User: Show me agent.py in langchain_agent1
→ read_github_file → Full file content.
```

### Comms Examples
```
User: What is AIXT staking?
→ Comms Agent → retrieve_comms_info → Docs summary + sources.
```

### Slack
```
User: Summarize latest Slack discussions in #general
→ retrieve_slack_history → Summary.
```

**UI Features**:
- Agent switching visualized.
- Tool steps expandable.
- Token usage tracked.
- Streaming responses.

## Slack Bot
1. Set `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`.
2. Run `python src/slack_server.py`.
3. @mention bot: "@bot What's new in AIXT?"

## Programmatic Access
```python
from src.agent import app
from langchain_core.messages import HumanMessage

config = {"configurable": {"thread_id": "session1"}}
result = app.invoke({"messages": [HumanMessage(content="Query here")]}, config)
print(result["messages"][-1].content)
```

## Ingestion Examples
```bash
# Add repo to config/github_repositories.json
python scripts/initialize_github_rag.py

# Assumes data/comms_pages_as_md/*.md populated
python scripts/initialize_local_md_rag.py
```

## API Reference
See [docs/modules.md](docs/modules.md) for modules/tools.

**Retriever**:
```python
from src.retrievers import get_hybrid_retriever
retriever = get_hybrid_retriever("./github.db", "github_repos", repo_filter="jenscodejens/langchain_agent1")
docs = retriever.invoke("agent.py content")
```

## Troubleshooting
- **No results**: Run ingestion scripts.
- **Port busy**: Set `CHAINLIT_PORT`.
- **Models slow**: Run `scripts/preload_models.py`.
- Logs: `logs/agent.log`, `logs/conversation_history.log`.
