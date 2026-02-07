from langchain_chroma import Chroma
from chromadb.config import Settings
from config.llm_config import embeddings
from langchain_core.documents import Document
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers.ensemble import EnsembleRetriever
from langchain.retrievers.contextual_compression import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder

# Global cache for reranker model to avoid reloading
_reranker_model = None

def get_hybrid_retriever(persist_dir, collection_name, repo_filter=None, top_n=5):
    """
    Creates a hybrid retriever for either GitHub or Comms agents.
    
    Args:
        persist_dir (str): Path to the Chroma DB (e.g., "./github.db" or "./planetix_comms.db")
        collection_name (str): Name of the collection (e.g., "github_repos" or "comms_docs")
        repo_filter (str, optional): Metadata filter for a specific repository.
        top_n (int): Number of final documents to return after reranking.
    """
    vectorstore = Chroma(
        persist_directory=persist_dir, 
        embedding_function=embeddings, 
        collection_name=collection_name,
        client_settings=Settings(anonymized_telemetry=False)
    )

    # Apply filter if provided (specific to GitHub logic)
    if repo_filter:
        all_data = vectorstore.get(where={"repo": repo_filter})
        dense_filter = {"repo": repo_filter}
    else:
        all_data = vectorstore.get()
        dense_filter = None

    # 1. Prepare BM25
    bm25_docs = [
        Document(page_content=content, metadata=meta) 
        for content, meta in zip(all_data['documents'], all_data['metadatas'])
    ]
    bm25_retriever = BM25Retriever.from_documents(bm25_docs)
    bm25_retriever.k = 10

    # 2. Prepare Dense Vector Search
    dense_retriever = vectorstore.as_retriever(
        search_type="similarity", 
        search_kwargs={"k": 10, "filter": dense_filter}
    )

    # 3. Combine in Ensemble
    # For Comms (text), BM25 is great for names/dates. For GitHub, it's great for filenames.
    ensemble = EnsembleRetriever(
        retrievers=[dense_retriever, bm25_retriever], 
        weights=[0.5, 0.5]
    )

    # 4. Reranking Layer (Cached Model)
    global _reranker_model
    if _reranker_model is None:
        _reranker_model = HuggingFaceCrossEncoder(model_name="BAAI/bge-reranker-v2-m3")
    
    reranker_compressor = CrossEncoderReranker(model=_reranker_model, top_n=top_n)

    # 5. Final Compressed Retriever
    return ContextualCompressionRetriever(
        base_compressor=reranker_compressor, 
        base_retriever=ensemble
    )
