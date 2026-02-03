from langchain.tools import tool
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper

ddg_api = DuckDuckGoSearchAPIWrapper(max_results=3)

@tool("web_search", description="Performs a websearch using DuckDuckGo. The LLM can choose what is relevant and how much information the reply should consist of depending on the query. Use this tool whenever you:- Need up-to-date information (news, current events, recent papers, prices, stats), don't already know the answer from training data- Want to verify / fact-check something. Use quotes for exact phrases, -exclude, site:domain.com, etc. when it helps.")
def duckduckgo_web_search(query: str) -> str:
    """ Simple web search using DuckDuckGo """
    try:
        # Use the standard wrapper for cleaner result handling
        return ddg_api.run(query)
    except Exception as e:
        # Let the middleware handle the exception bubble-up
        raise RuntimeError(f"Search failed for query '{query}': {str(e)}")