from langchain_chroma import Chroma
from config.llm_config import embeddings
from langchain_core.documents import Document
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers.ensemble import EnsembleRetriever
from langchain.retrievers.contextual_compression import ContextualCompressionRetriever

# Retrieve it from the top level of compressors instead of the cross_encoder file
from langchain.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder

# Global cache for reranker model to avoid reloading
_reranker_model = None

def get_hybrid_retriever(persist_dir="./github.db", repo_filter=None):
    """
    Creates a hybrid retriever combining dense vector search, BM25 sparse retrieval, and cross-encoder reranking.

    Args:
        persist_dir (str): Directory where the Chroma vectorstore is persisted. Defaults to "./github.db".
        repo_filter (str, optional): Filter to apply for specific repository. If provided, only data from that repo is used.

    Returns:
        ContextualCompressionRetriever: The configured hybrid retriever.
    """
    vectorstore = Chroma(
        persist_directory=persist_dir, 
        embedding_function=embeddings, 
        collection_name="github_repos"
    )

    if repo_filter:
        all_data = vectorstore.get(where={"repo": repo_filter})
        dense_filter = {"repo": repo_filter}
    else:
        all_data = vectorstore.get()
        dense_filter = None

    bm25_docs = [
        Document(page_content=content, metadata=meta) 
        for content, meta in zip(all_data['documents'], all_data['metadatas'])
    ]

    bm25_retriever = BM25Retriever.from_documents(bm25_docs)
    bm25_retriever.k = 10

    dense_retriever = vectorstore.as_retriever(
        search_type="similarity", 
        search_kwargs={"k": 10, "filter": dense_filter}
    )

    ensemble = EnsembleRetriever(
        retrievers=[dense_retriever, bm25_retriever], 
        weights=[0.5, 0.5]
    )

    # Initialize Cross-Encoder for Reranking (cached to avoid reloading)
    global _reranker_model
    if _reranker_model is None:
        _reranker_model = HuggingFaceCrossEncoder(model_name="BAAI/bge-reranker-v2-m3")
    model = _reranker_model
    reranker_compressor = CrossEncoderReranker(model=model, top_n=5)

    retriever = ContextualCompressionRetriever(
        base_compressor=reranker_compressor, 
        base_retriever=ensemble
    )

    return retriever
