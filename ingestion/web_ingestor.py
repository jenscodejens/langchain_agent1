import json
import logging
import re
from langchain_core.documents import Document
import trafilatura
from playwright.sync_api import sync_playwright
from .base_ingestor import BaseIngestor

logger = logging.getLogger(__name__)

def clean_text(text):
    """
    Clean and normalize whitespace in the given text.

    Args:
        text (str): The input text to clean.

    Returns:
        str: The cleaned text with normalized whitespace.
    """
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text).strip()

class WebIngestor(BaseIngestor):
    def __init__(self, config_path: str, persist_directory: str = "./planetix_comms.db", collection_name: str = "comms_docs"):
        super().__init__(persist_directory, collection_name)
        with open(config_path, 'r') as f:
            config = json.load(f)
        self.urls = config.get('comms_docs', [])

    def load_documents(self) -> list[Document]:
        """Load documents from web URLs."""
        documents = []

        for url in self.urls:
            logger.info(f"Processing: {url}")
            docs = self._fetch_and_process_url(url)
            documents.extend(docs)

        return documents

    def _fetch_and_process_url(self, url: str) -> list[Document]:
        """Fetch and process content from a URL."""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, wait_until='networkidle')
                downloaded = page.content()
            if not downloaded:
                logger.warning(f"Could not fetch content from: {url}")
                return []

            # Extract metadata (date, title, etc.) automatically
            meta_data = trafilatura.extract_metadata(downloaded)
            text = trafilatura.extract(
                downloaded,
                include_comments=False,
                include_tables=True,
                no_fallback=False,
                favor_precision=True,
            )

            cleaned_text = clean_text(text)
            if cleaned_text:
                # Build metadata object
                metadata = {
                    "url": url,
                    "title": str(meta_data.title) if meta_data and meta_data.title else "Unknown title",
                    "language": "text"  # Placeholder to match GitHub metadata structure
                }
                # Filter out None values for Chroma compatibility
                metadata = {k: str(v) for k, v in metadata.items() if v is not None}

                return [Document(page_content=cleaned_text, metadata=metadata)]
            return []
        except Exception as e:
            logger.error(f"Error processing {url}: {e}")
            return []

    def run_ingestion(self):
        """Override to use specific splitter for web content."""
        logger.info(f"Starting web ingestion for {len(self.urls)} URLs")
        documents = self.load_documents()
        if not documents:
            logger.warning("No documents loaded.")
            return

        # Use simpler splitter for web content
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=100,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        split_docs = splitter.split_documents(documents)
        valid_docs = [d for d in split_docs if len(d.page_content.strip()) > 100]

        if valid_docs:
            ids = self.generate_ids(valid_docs)
            self.save_to_vectorstore(valid_docs, ids)
            logger.info(f"Web ingestion complete: {len(valid_docs)} chunks in {self.persist_directory}")
        else:
            logger.warning("No valid documents to save.")