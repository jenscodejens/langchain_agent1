import os
from pathlib import Path
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter, Language
from .base_ingestor import BaseIngestor
import logging

logger = logging.getLogger(__name__)

class LocalMDIngestor(BaseIngestor):
    def __init__(self, folder_path: str, persist_directory: str = "./planetix_comms.db", collection_name: str = "comms_docs"):
        super().__init__(persist_directory, collection_name)
        self.folder_path = folder_path

    def load_documents(self) -> list[Document]:
        """Load documents from local Markdown files."""
        documents = []
        data_path = Path(self.folder_path)

        if not data_path.exists():
            logger.error(f"Directory not found: {self.folder_path}")
            return []

        for file_path in data_path.glob("*.md"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Clean filename for title
                title = file_path.stem.replace("_", " ").title()

                # Metadata construction (syncing keys with GitHub RAG for consistency)
                metadata = {
                    "url": f"local://{file_path.name}",
                    "title": title,
                    "language": "markdown"  # Explicitly set to trigger markdown splitting logic
                }

                # Ensure all metadata values are strings for Chroma compatibility
                metadata = {k: str(v) for k, v in metadata.items() if v is not None}

                documents.append(Document(page_content=content, metadata=metadata))
                logger.info(f"Loaded: {file_path.name}")

            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")

        return documents

    def run_ingestion(self):
        """Override to use markdown-specific splitter."""
        logger.info(f"Starting local MD ingestion from: {self.folder_path}")
        documents = self.load_documents()
        if not documents:
            logger.warning("No documents loaded.")
            return

        # Use markdown-aware splitter
        splitter = RecursiveCharacterTextSplitter.from_language(
            language=Language.MARKDOWN,
            chunk_size=1000,
            chunk_overlap=150
        )
        split_docs = splitter.split_documents(documents)

        # Filter out very small chunks (junk/formatting artifacts)
        valid_docs = [d for d in split_docs if len(d.page_content.strip()) > 100]

        if valid_docs:
            ids = self.generate_ids(valid_docs)
            self.save_to_vectorstore(valid_docs, ids)
            logger.info(f"Local MD ingestion complete: {len(valid_docs)} chunks in {self.persist_directory}")
        else:
            logger.warning("No valid documents to save.")