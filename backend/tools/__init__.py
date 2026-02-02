from .current_datetime import current_datetime
from .retrieve_github_info import retrieve_github_info
from .list_tracked_repositories import list_tracked_repositories
from .duckduckgo_web_search import duckduckgo_web_search
from .read_github_file import read_github_file

"""
Available tools:
----------------
retrieve_github_info
list_tracked_repositories
read_github_file

duckduckgo_web_search
current_datetime
"""

# List of tools the agent has access to.
all_tools = [current_datetime, retrieve_github_info, list_tracked_repositories]
tool_dict = {tool.name: tool for tool in all_tools}

# Tool groupings for multi-agent system
shared_tools = [current_datetime]
github_tools = [retrieve_github_info, list_tracked_repositories, read_github_file]
comms_tools = []  # placeholders for email_send, chat_notify, retrieve_comms_docs
general_tools = [duckduckgo_web_search]

github_agent_tools = shared_tools + github_tools
comms_agent_full_tools = shared_tools + comms_tools
general_full_tools = shared_tools + general_tools

github_agent_tool_dict = {tool.name: tool for tool in github_agent_tools}
comms_agent_tool_dict = {tool.name: tool for tool in comms_agent_full_tools}
general_tool_dict = {tool.name: tool for tool in general_full_tools}