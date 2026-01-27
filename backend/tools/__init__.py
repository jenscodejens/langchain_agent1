from .current_datetime import current_datetime
from .retrieve_github_info import retrieve_github_info
from .list_tracked_repositories import list_tracked_repositories
from .duckduckgo_web_search import duckduckgo_web_search

# Available tools:
#
# current_datetime
# retrieve_github_info
# list_tracked_repositories
# duckduckgo_web_search

# List of tools the agent has access to.
all_tools = [current_datetime, retrieve_github_info, list_tracked_repositories]
tool_dict = {tool.name: tool for tool in all_tools}