# from langchain.tools import tool
# from backend.retrievers import get_hybrid_retriever
# import json

# @tool("retrieve_comms_info", description="Retrieve relevant information from communications documents using hybrid search.")
# def comms_retriever(query: str) -> str:
#     """Retrieves and returns relevant comms information based on the query."""

#     retriever = get_hybrid_retriever(
#     persist_dir="./planetix_comms.db", 
#     collection_name="comms_docs", 
#     top_n=3
# )
#     docs = retriever.invoke(query)
#     return "\n\n".join([doc.page_content for doc in docs])
from langchain.tools import tool
from backend.retrievers import get_hybrid_retriever

@tool("retrieve_comms_info", description="Retrieve information from PlanetIX announcements and AIXT news. Use this for project updates, news, or general community information.")
def retrieve_comms_info(query: str) -> str:
    """Retrieve news and announcement context from the Comms RAG database."""
    try:
        # Initialize the same shared hybrid retriever but for Comms
        retriever = get_hybrid_retriever(
            persist_dir="./planetix_comms.db", 
            collection_name="comms_docs", 
            repo_filter=None, # No repo filter needed for web docs
            top_n=3          # More precise focus for text news
        )
        
        docs = retriever.invoke(query)

        # Format output with URL and Title
        context = "\n\n".join([
            f"Source: {doc.metadata.get('url', 'Unknown URL')}\n"
            f"Title: {doc.metadata.get('title', 'Unknown Title')}\n"
            f"{doc.page_content}" 
            for doc in docs
        ])
        return context
    except Exception as e:
        return f"Comms Retrieval failed: {str(e)}"
