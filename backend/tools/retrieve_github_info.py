from langchain.tools import tool
from backend.retrievers import get_hybrid_retriever
import json

@tool("retrieve_github_info", description="Retrieve technical information from GitHub repositories. Best for code, architecture, and file-specific questions. Automatically handles hyphen-matching for repo names.")
def retrieve_github_info(query: str) -> str:
    """Retrieve technical context from the GitHub RAG database."""
    try:
        # Load repo list to identify if a specific repo is mentioned in the query
        with open('config/github_repositories.json', 'r') as f:
            config = json.load(f)
        known_repos = config['github_repos']

        selected_repo = None
        for repo in known_repos:
            repo_short = repo.split('/')[-1]
            repo_no_hyphen = repo_short.replace('-', '')
            if repo_short in query.lower() or repo_no_hyphen in query.lower() or repo in query:
                selected_repo = repo
                break

        # Initialize the shared hybrid retriever for GitHub
        retriever = get_hybrid_retriever(
            persist_dir="./github.db", 
            collection_name="github_repos", 
            repo_filter=selected_repo, 
            top_n=5
        )
        
        docs = retriever.invoke(query)

        # Format output with GitHub blob links
        context = "\n\n".join([
            f"Source: https://github.com{doc.metadata.get('repo', 'unknown')}/blob/main/{doc.metadata.get('source', 'unknown')}\n"
            f"Language: {doc.metadata.get('language', 'unknown')}\n"
            f"{doc.page_content}" 
            for doc in docs
        ])
        return context
    except Exception as e:
        return f"GitHub Retrieval failed: {str(e)}"
