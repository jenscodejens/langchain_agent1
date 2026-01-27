from langchain.tools import tool
from langchain_chroma import Chroma
from config.llm_config import embeddings

@tool("retrieve_github_info", description="Retrieve relevant information from GitHub repositories stored in the RAG database. Use this for questions about code, repositories, or technical details from the configured GitHub repos. Show the code snippet(s) from where you base your response on. Note: Users often omit hyphens in repo names (e.g., 'docragtest' for 'doc-rag-test'). If a repository name is mentioned without hyphens, automatically attempt to match it to its hyphenated equivalent in the database.")
def retrieve_github_info(query: str) -> str:
    """ Retrieve context from GitHub repos """
    try:
        vectorstore = Chroma(persist_directory="./chroma_db", embedding_function=embeddings, collection_name="github_repos")
        docs = vectorstore.similarity_search(query, k=5)
        context = "\n\n".join([f"Source: {doc.metadata.get('source', 'unknown')}\nLanguage: {doc.metadata.get('language', 'unknown')}\n{doc.page_content}" for doc in docs])
        return context
    except Exception as e:
        return f"Retrieval failed: {str(e)}"