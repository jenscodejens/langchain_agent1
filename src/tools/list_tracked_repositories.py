import json
import os
from langchain.tools import tool

@tool("list_tracked_repositories", description="Lists all GitHub repositories currently tracked in the RAG database, including their author/repo names and direct links to the repositories on GitHub.")
def list_tracked_repositories(_: str = "") -> str:
    """Reads the 'github_repos' list from config.json and formats the repositories with clickable links."""
    try:
        config_path = os.path.join(os.path.dirname(__file__), '../../config/github_repositories.json')
        with open(config_path, 'r') as f:
            config = json.load(f)
        repos = config.get('github_repos', [])
        if not repos:
            return ""
        result = ""
        for repo in repos:
            author, repo_name = repo.split('/', 1)
            result += f"{author} - **{repo_name}**&emsp;[GitHub](https://github.com/{repo})\n"
        return result
    except Exception as e:
        return f"Failed to retrieve repository list: {str(e)}"