# Configuration Files

## config/llm_config.py
Defines global LLM and embeddings:
- `embeddings`: HuggingFaceEmbeddings("BAAI/bge-m3", device=mps/cuda/cpu).
- `llm_model`: ChatXAI("grok-4-1-fast-reasoning", temperature=0, streaming=True).

## config/github_repositories.json
Tracked GitHub repos for ingestion:
```json
{
  "github_repos": [
    "jenscodejens/langchain_agent1",
    "indiano881/ai-agentic-repo-test"
  ]
}
```
Used by `list_tracked_repositories` tool and ingestion.

## config/comms.json
Web URLs for Comms ingestion (currently unused in local_md script):
```json
{
  "comms_docs": ["https://comms.planetix.com/AIXT"]
}
```

## System Messages (*.md)
Loaded dynamically by agents:

### config/supervisor_systemmessage.md
Supervisor routing logic: Classify to "github_agent", "comms_agent", or "ambiguous".

### config/github_systemmessage.md
**Stack von Overflow** persona:
- Grumpy for casual; professional for tech.
- Tools: `list_tracked_repositories` first, then `read_github_file` or `retrieve_github_info`.
- Strict no-hallucination, cite sources.

### config/comms_systemmessage.md
**PlanetIX Dispatch**:
- Fact-only from Comms DB/Slack.
- Structure: Summary → Details → Sources.
- Use `retrieve_comms_info`, `retrieve_slack_history`.

## Environment Variables (.env)
```

XAI_API_KEY=

SLACK_BOT_TOKEN=

SLACK_APP_TOKEN=

SLACK_CHANNEL_ID=...  # Required for retrieve_slack_history tool

NGROK_AUTHTOKEN=...

NGROK_DOMAIN=...

CHAINLIT_PORT=8000

```
