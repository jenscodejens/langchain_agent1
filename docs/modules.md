# Core Modules Documentation

## src/agent.py
**Purpose**: Defines the LangGraph multi-agent workflow.

### Key Components
- **AgentState**: TypedDict with `messages` (LangChain messages) and `next` (routing).
- **RouterResponse**: Pydantic model for supervisor output (`next_node`: github_agent/comms_agent/ambiguous).
- **Agents**:
  - `github_agent_call`: LLM bound to GitHub tools + system prompt from `config/github_systemmessage.md`.
  - `comms_agent_call`: LLM bound to Comms tools + system prompt from `config/comms_systemmessage.md`.
- **Tool Executors**: `_execute_tools`, `github_agent_tool_exec`, `comms_agent_tool_exec`.
- **Supervisor**: `supervisor` node uses structured output to route queries.
- **Graph**: StateGraph with conditional edges, loops for tool calls, compiled with InMemorySaver.

**Exports**: `app` (compiled graph).

## src/retrievers.py
**Purpose**: Hybrid RAG retriever for both GitHub and Comms.

### `get_hybrid_retriever(persist_dir, collection_name, repo_filter=None, top_n=5)`
- **Vectorstore**: Chroma with bge-m3 embeddings.
- **BM25Retriever**: From all docs in collection.
- **EnsembleRetriever**: 50/50 dense + sparse, k=10.
- **ContextualCompressionRetriever**: CrossEncoderReranker (bge-reranker-v2-m3) for final top_n.
- **Filtering**: Optional `repo` metadata filter for GitHub.

**Globals**: Cached `_reranker_model`.

## src/tools/
**Purpose**: LangChain `@tool`-decorated functions for agents.

### Tool Groupings (from `src/tools/__init__.py`)
- **Shared**: `current_datetime`
- **GitHub Tools**:
  | Tool | Description |
  |------|-------------|
  | `retrieve_github_info(query, repo=None)` | Hybrid RAG search in GitHub DB. Returns top docs. |
  | `list_tracked_repositories()` | Lists repos from `config/github_repositories.json`. |
  | `read_github_file(repo, path)` | Fetches raw file content from GitHub API. |
- **Comms Tools**:
  | Tool | Description |
  |------|-------------|
  | `retrieve_comms_info(query)` | Hybrid RAG search in PlanetIX Comms DB. |
  | `retrieve_slack_history(channel, limit=50)` | Fetches recent Slack messages (requires tokens). |

### Additional Tools
- `duckduckgo_web_search` (commented out).
- Dicts: `github_agent_tool_dict`, etc. for binding.

**Usage**: Imported in `agent.py` for LLM binding.

## Other Key Modules
- **src/app.py**: Chainlit integration, streams LangGraph events, tool steps, logging.
- **config/llm_config.py**: `embeddings` (HuggingFace bge-m3), `llm_model` (ChatXAI Grok).
- **src/run_chainlit.py**: Launcher with port check, watch/debug flags.
- **src/slack_server.py**: Slack Bolt + Flask bridge to LangGraph.
