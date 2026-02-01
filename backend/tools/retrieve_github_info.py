from langchain.tools import tool
from backend.retrievers import get_hybrid_retriever
import json

@tool("retrieve_github_info", description="Retrieve relevant information from GitHub repositories stored in the RAG database. Use this for questions about code, repositories, or technical details from the configured GitHub repos. Show the code snippet(s) from where you base your response on. Note: Users often omit hyphens in repo names (e.g., 'docragtest' for 'doc-rag-test'). If a repository name is mentioned without hyphens, automatically attempt to match it to its hyphenated equivalent in the database.")
def retrieve_github_info(query: str) -> str:
    """ Retrieve context from GitHub repos """
    try:
        # Load config for known repos
        with open('config/github_repositories.json', 'r') as f:
            config = json.load(f)
        known_repos = config['github_repos']

        # Detect repository mentions in query for filtering
        repo_filters = []
        for repo in known_repos:
            repo_short = repo.split('/')[-1]
            repo_no_hyphen = repo_short.replace('-', '')
            if repo_short in query.lower() or repo_no_hyphen in query.lower() or repo in query:
                repo_filters.append(repo)

        repo_filter = repo_filters[0] if repo_filters else None

        retriever = get_hybrid_retriever(repo_filter=repo_filter)
        docs = retriever.invoke(query)

        context = "\n\n".join([f"Source: https://github.com/{doc.metadata.get('repo', 'unknown')}/blob/main/{doc.metadata.get('source', 'unknown')}\nLanguage: {doc.metadata.get('language', 'unknown')}\n{doc.page_content}" for doc in docs])
        return context
    except Exception as e:
        return f"Retrieval failed: {str(e)}"