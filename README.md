###  *Project under construction, I'm in the process of learning Python and LangChain currently.*
<br><br>

# AI Assistant with GitHub RAG

AI assistant built with Chainlit, LangGraph, and HuggingFace embeddings, featuring Retrieval-Augmented Generation (RAG) for GitHub repository information.

## 🚀 Features

- **Conversational AI**: Powered by xAI's Grok-4-1-fast-reasoning model
- **GitHub RAG**: Search and retrieve information from indexed GitHub repositories
- **Tool Integration**: Date/time lookup, web search, and text summarization
- **Modern Web UI**: Chainlit-based interface with custom styling
- **Copy-to-Clipboard**: Easy message copying with visual feedback
- **Local Embeddings**: BAAI/bge-m3 model for privacy-preserving text embeddings
- **GPU Support**: Automatic GPU/CPU detection for optimal performance

## 🛠️ Tech Stack

- **Frontend**: Chainlit (React-based web UI)
- **Backend**: Python with LangGraph for agent orchestration
- **AI/ML**: 
  - xAI ChatXAI for conversational AI
  - HuggingFace BAAI/bge-m3 for embeddings
  - ChromaDB for vector storage
- **Tools**: DuckDuckGo search, GitHub API integration
- **Package Management**: uv (fast Python package manager)

## 📋 Prerequisites

- Python 3.8+
- uv package manager
- GitHub Personal Access Token (for repository access)

## 🔧 Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/jenscodejens/langchain_agent1
   cd <project-directory>
   ```

2. **Install dependencies**
   ```bash
   uv sync
   ```

3. **Set up environment variables**
   Create a `.env` file:
   ```env
   # Add your API keys and configuration
   GITHUB_TOKEN=your_github_token_here
   ```

4. **Initialize the RAG database** (optional, if you have GitHub repos to index)
   ```bash
   uv run python initialize_rag.py
   ```

## 🚀 Usage

1. **Start the application**
   ```bash
   uv run python backend/run_chainlit.py
   ```

2. **Open your browser**
   Navigate to `http://localhost:8000`

3. **Start chatting**
   Ask questions about GitHub repositories or general queries. The AI will use tools as needed.

## ⚙️ Configuration

### LLM Configuration (`backend/llm_config.py`)
- Model: xAI Grok-4-1-fast-reasoning
- Embeddings: BAAI/bge-m3 with automatic device detection
- Cache location: `./embedding_model`

### Tools Available
- `current_datetime`: Get current date and time
- `retrieve_github_info`: Search GitHub repository information
- `summarize_text`: Condense long text content

### Custom UI Features (`public/custom.js`)
- Copy-to-clipboard buttons for messages
- Theme-aware AI avatars
- Custom styling and interactions

## 📁 Project Structure

```
├── backend/
│   ├── agent.py          # LangGraph agent with tool definitions
│   ├── llm_config.py     # LLM and embeddings configuration
│   ├── main.py           # Chainlit message handlers
│   └── run_chainlit.py   # Application startup script
├── public/
│   ├── custom.js         # Frontend customizations
│   └── *.svg             # Theme assets
├── Diagrams/
│   ├── tool_handling.png
│   └── workflow_incl_chainlit.png
├── initialize_rag.py     # RAG database setup
├── pyproject.toml        # Project dependencies
├── uv.lock               # Dependency lock file
└── README.md             # This file
```

## 🔍 Key Components

### Agent Workflow
The system uses LangGraph to orchestrate:
1. User input processing
2. Tool calling decisions
3. Information retrieval and synthesis
4. Response generation

### RAG Implementation
- **Ingestion**: GitHub repositories indexed with BAAI/bge-m3 embeddings
- **Retrieval**: Similarity search in ChromaDB vector store
- **Generation**: Context-augmented responses from xAI LLM

### Web Interface
- **Chainlit UI**: Modern chat interface with streaming responses
- **Custom Features**: Message copying, theme switching, avatar updates
- **Responsive Design**: Works on desktop and mobile

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
