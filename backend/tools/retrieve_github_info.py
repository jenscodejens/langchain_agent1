from langchain.tools import tool
from langchain_chroma import Chroma
from config.llm_config import embeddings

@tool("retrieve_github_info", description="Retrieve relevant information from GitHub repositories stored in the RAG database. Use this for questions about code, repositories, or technical details from the configured GitHub repos. Show the code snippet(s) from where you base your response on. Note: Users often omit hyphens in repo names (e.g., 'docragtest' for 'doc-rag-test'). If a repository name is mentioned without hyphens, automatically attempt to match it to its hyphenated equivalent in the database.")
def retrieve_github_info(query: str) -> str:
    """ Retrieve context from GitHub repos """
    try:
        vectorstore = Chroma(persist_directory="./chroma_db", embedding_function=embeddings, collection_name="github_repos")

        # Detect repository mentions in query for filtering
        repo_filters = []
        known_repos = ["jenscodejens/doc-rag-test", "indiano881/ai-agentic-repo-test"]  # Should load from config

        for repo in known_repos:
            repo_short = repo.split('/')[-1]  # e.g., "doc-rag-test"
            repo_no_hyphen = repo_short.replace('-', '')  # e.g., "docragtest"
            if repo_short in query.lower() or repo_no_hyphen in query.lower() or repo in query:
                repo_filters.append(repo)

        if repo_filters:
            # Get all documents and filter by repo
            all_docs = vectorstore.get(include=['metadatas', 'documents', 'embeddings'])
            filtered_docs = []
            for i, metadata in enumerate(all_docs['metadatas']):
                if metadata.get('repo') in repo_filters:
                    # Create a mock doc object for similarity search
                    class MockDoc:
                        def __init__(self, page_content, metadata, embedding):
                            self.page_content = page_content
                            self.metadata = metadata
                            self.embedding = embedding
                    filtered_docs.append(MockDoc(all_docs['documents'][i], metadata, all_docs['embeddings'][i]))

            if filtered_docs:
                # Sort by similarity to query (simple cosine similarity)
                import numpy as np
                query_embedding = embeddings.embed_query(query)
                similarities = []
                for doc in filtered_docs:
                    similarity = np.dot(query_embedding, doc.embedding) / (np.linalg.norm(query_embedding) * np.linalg.norm(doc.embedding))
                    similarities.append((similarity, doc))

                similarities.sort(key=lambda x: x[0], reverse=True)
                docs = [doc for _, doc in similarities[:5]]
            else:
                docs = []
        else:
            docs = vectorstore.similarity_search(query, k=5)

        context = "\n\n".join([f"Source: https://github.com/{doc.metadata.get('repo', 'unknown')}/blob/main/{doc.metadata.get('source', 'unknown')}\nLanguage: {doc.metadata.get('language', 'unknown')}\n{doc.page_content}" for doc in docs])
        return context
    except Exception as e:
        return f"Retrieval failed: {str(e)}"