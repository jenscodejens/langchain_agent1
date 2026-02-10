import os
import httpx
from langchain.tools import tool
from dotenv import load_dotenv

load_dotenv()

@tool("read_github_file", description="Read the COMPLETE content of a specific file from a GitHub repository using the Raw API. Use this when the user asks for the full content of a file (like a README.md). You must provide the repo_name (e.g., 'user/repo') and the exact file_path.")
def read_github_file(repo_name: str, file_path: str) -> str:
    """Fetch full file content directly from GitHub's Raw API for the 'main' branch."""
    
    # Construction of the direct Raw URL
    raw_url = f"https://raw.githubusercontent.com/{repo_name}/main/{file_path}"
    
    # Retrieve GITHUB_TOKEN for private repository access
    token = os.getenv("GITHUB_TOKEN")
    headers = {
        "Authorization": f"token {token}" if token else "",
        "User-Agent": ""
    }

    try:
        # trust_env=False fixed your 'getaddrinfo' error in the terminal test
        # follow_redirects=True handles the 301/302 status codes correctly
        with httpx.Client(
            timeout=15.0, 
            trust_env=False, 
            follow_redirects=True 
        ) as client:
            response = client.get(raw_url, headers=headers)
            
            if response.status_code == 200:
                return f"Full content of {file_path} from {repo_name}:\n\n{response.text}"
            elif response.status_code == 404:
                return f"Error: File '{file_path}' not found on 'main' branch in '{repo_name}'. Check path and repo name."
            else:
                return f"Error: GitHub API returned status code {response.status_code}."

    except Exception as e:
        return f"Request failed: {str(e)}. This might be a local network or DNS issue."
