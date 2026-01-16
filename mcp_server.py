from fastmcp import FastMCP
import requests
from bs4 import BeautifulSoup
import json

mcp = FastMCP("Docs by LangChain")

@mcp.tool()
def ExtractLangChainDocContent(url: str) -> str:
    """
    Extract text content from a LangChain documentation page for use by MCP functionality.

    Args:
        url: The URL of the LangChain documentation page to extract text from

    Returns:
        The extracted text content from the page
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.extract()

            # Get text
            text = soup.get_text()

            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)

            return text
        else:
            return f"Failed to fetch page: HTTP {response.status_code}"

    except Exception as e:
        return f"Error extracting content: {str(e)}"

if __name__ == "__main__":
    mcp.run()