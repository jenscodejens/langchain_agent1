from datetime import datetime
from langchain.tools import tool

@tool("get_date_and_time", description="Returns the current date and time.") 
def current_datetime(_: str = "") -> str:
     """ Returns the current date and time in multiple formats. The LLM can choose which part to use. """ 
     now = datetime.now()
     return {
             "date": now.strftime("%Y-%m-%d"),
             "time": now.strftime("%H:%M"),
             "datetime": now.strftime("%Y-%m-%d %H:%M")
             }