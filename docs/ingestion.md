# Ingestion Pipeline & Data Sources

## Overview
Modular ingestion system populates Chroma vector stores (`github.db`, `planetix_comms.db`) for RAG.

- **Base Class**: `ingestion/base_ingestor.py` - Embeddings, splitting (language-aware), ID generation (hash), save.
- **Chunking**: RecursiveCharacterTextSplitter (chunk_size=800-1500, overlap=100-150), language-specific (Python/JS/etc.).
- **Scripts**: Wrappers in `scripts/` to run ingestors.

## Ingestors

### GitHub (`ingestion/github_ingestor.py`)
- **Input**: Repos from `config/github_repositories.json`.
- **Process**:
  1. GitLoader clones main/default branch to temp/.
  2. `advanced_file_filter`: Code/config files, ignore .git/node_modules/etc.
  3. Language-aware splitting.
  4. IDs: `repo_source_contenthash`.
  5. Metadata: `repo`, `source`.
- **Script**: `scripts/initialize_github_rag.py`
- **Output**: `github.db` ("github_repos")

### Local MD (`ingestion/local_md_ingestor.py`)
- **Input**: `data/comms_pages_as_md/*.md` (PlanetIX announcements).
- **Process**: Load MD, title from filename, Markdown splitter (chunk_size=1000), filter >100 chars.
- **Script**: `scripts/initialize_local_md_rag.py`
- **Output**: `planetix_comms.db` ("comms_docs")

### Web (`ingestion/web_ingestor.py`)
- **Input**: URLs from `config/comms.json`.
- **Process**: Trafilatura fetch/extract/metadata, clean text, simple splitter.
- **Script**: `scripts/initialize_comms_web_rag.py`
- **Output**: `planetix_comms.db`

## Data Sources
- **Comms MD**: `data/comms_pages_as_md/` (e.g., aix-calculator.md, aixt.md).
- **GitHub**: Dynamic from config (clones on ingest).
- **Slack**: Live via `retrieve_slack_history` tool (no ingestion).

## Running Ingestion
```bash
python scripts/initialize_github_rag.py
python scripts/initialize_local_md_rag.py
```
- Progress bar, temp cleanup, logging.
- Re-run overwrites (commented check).

## Notes
- Embeddings: bge-m3 (global).
- Temp dirs cleaned post-ingest.
- Unique IDs prevent duplicates.
