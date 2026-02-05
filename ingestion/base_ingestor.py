import os
from abc import ABC, abstractmethod
from typing import Optional
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter, Language
from langchain_core.documents import Document
import hashlib
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class BaseIngestor(ABC):
    def __init__(self, persist_directory: str, collection_name: str):
        self.embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-m3")
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.vectorstore = Chroma(
            embedding_function=self.embeddings,
            persist_directory=persist_directory,
            collection_name=collection_name
        )

    @abstractmethod
    def load_documents(self) -> list[Document]:
        """Load documents from the specific source."""
        pass

    def split_documents(self, documents: list[Document]) -> list[Document]:
        """Split documents using language-aware splitting."""
        split_docs = []
        ext_to_language = {
            ".py": Language.PYTHON,
            ".pyi": Language.PYTHON,
            ".js": Language.JS,
            ".jsx": Language.JS,
            ".ts": Language.TS,
            ".tsx": Language.TS,
            ".java": Language.JAVA,
            ".kt": Language.KOTLIN,
            ".rs": Language.RUST,
            ".go": Language.GO,
            ".c": Language.C,
            ".cpp": Language.CPP,
            ".h": Language.CPP,
            ".hpp": Language.CPP,
            ".cs": Language.CSHARP,
            ".swift": Language.SWIFT,
            ".php": Language.PHP,
            ".rb": Language.RUBY,
            ".md": Language.MARKDOWN,
            ".markdown": Language.MARKDOWN,
            ".html": Language.HTML,
        }

        for doc in documents:
            source_path = doc.metadata.get("source", "")
            _, ext = os.path.splitext(source_path)
            ext = ext.lower()

            language = ext_to_language.get(ext)
            if language:
                splitter = RecursiveCharacterTextSplitter.from_language(
                    language=language,
                    chunk_size=1500,
                    chunk_overlap=150,
                )
            else: # Default language is set to None
                splitter = RecursiveCharacterTextSplitter(
                    chunk_size=1500,
                    chunk_overlap=150,
                )
            chunks = splitter.split_documents([doc])
            split_docs.extend(chunks)

        return split_docs

    def save_to_vectorstore(self, documents: list[Document], ids: Optional[list[str]] = None):
        """Save documents to vectorstore with optional IDs."""
        if ids:
            self.vectorstore.add_documents(documents, ids=ids)
        else:
            self.vectorstore.add_documents(documents)

    def generate_ids(self, documents: list[Document]) -> list[str]:
        """Generate unique IDs for documents."""
        ids = []
        for doc in documents:
            # Create a unique identifier by combining the document's URL and the first 50 characters of its content
            identifier = f"{doc.metadata.get('url', '')}_{doc.page_content[:50]}"
            # Generate an MD5 hash of the identifier to create a fixed-length, unique ID
            ids.append(hashlib.md5(identifier.encode()).hexdigest())
        return ids

    def run_ingestion(self):
        """Run the full ingestion pipeline."""
        logger.info("Starting document ingestion...")
        documents = self.load_documents()
        if not documents:
            logger.warning("No documents loaded.")
            return

        split_docs = self.split_documents(documents)
        valid_docs = [d for d in split_docs if isinstance(d.page_content, str) and d.page_content.strip()]

        if valid_docs:
            ids = self.generate_ids(valid_docs)
            self.save_to_vectorstore(valid_docs, ids)
            logger.info(f"Added {len(valid_docs)} chunks to {self.persist_directory}")
        else:
            logger.warning("No valid documents to save.")