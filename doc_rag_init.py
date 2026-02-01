import json
import logging
import re
import hashlib
from dateutil import parser as date_parser
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
import trafilatura
from langchain_core.documents import Document

# Logging setup
logging.basicConfig(level=logging.INFO)
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

def indexing_pipeline(url):
    """
    Fetch and process content from a URL using Trafilatura, extracting text and metadata.

    Args:
        url (str): The URL to fetch content from.

    Returns:
        list[Document]: A list containing a Document object with cleaned text and metadata, or empty list on failure.
    """
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            logger.warning(f"Could not fetch content from: {url}")
            return []
        
        # Extract metadata (date, title, etc.) automatically
        meta_data = trafilatura.extract_metadata(downloaded)
        text = trafilatura.extract(downloaded, include_comments=False)
        
        cleaned_text = clean_text(text)
        if cleaned_text:
            # Build metadata object
            metadata = {
                "url": url,
                "title": str(meta_data.title) if meta_data and meta_data.title else "Unknown title",
                "publish_date": str(meta_data.date) if meta_data and meta_data.date else None
            }
            # Filter out None values for Chroma compatibility
            metadata = {k: v for k, v in metadata.items() if v is not None}
            
            return [Document(page_content=cleaned_text, metadata=metadata)]
        return []
    except Exception as e:
        logger.error(f"Error processing {url}: {e}")
        return []

# Configuration & Embeddings
with open('config/comms.json', 'r') as f:
    config = json.load(f)

# BGE-M3 is powerful, but requires good chunks to perform
embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-m3")
persist_directory = "./planetix_comms.db"

# Initialize Chroma
vectorstore = Chroma(
    embedding_function=embeddings,
    persist_directory=persist_directory,
    collection_name="comms_docs"
)

# Splitter settings
splitter = RecursiveCharacterTextSplitter(
    chunk_size=800, 
    chunk_overlap=100,
    separators=["\n\n", "\n", ". ", " ", ""]
)

all_documents = []

# Loop through URLs in configuration
urls = config.get('comms_docs', [])
logger.info(f"Found {len(urls)} URLs in config.")

for url in urls:
    logger.info(f"Processing: {url}")
    docs = indexing_pipeline(url)
    
    for doc in docs:
        # If Trafilatura missed the date, run your old regex-fallback here if needed
        if 'publish_date' not in doc.metadata:
            date_regex = r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2}|\w+ \d{1,2}, \d{4})\b'
            match = re.search(date_regex, doc.page_content[:500])
            if match:
                try:
                    doc.metadata['publish_date'] = date_parser.parse(match.group(1)).isoformat()
                except (ValueError, OverflowError):
                    pass
        
        all_documents.append(doc)

# Splitting and Save with Double Check (Upsert logic)
if all_documents:
    split_docs = splitter.split_documents(all_documents)
    valid_docs = [d for d in split_docs if len(d.page_content.strip()) > 20]
    
    if valid_docs:
        # Create unique IDs based on content and URL to avoid duplicates
        ids = []
        for d in valid_docs:
            identifier = f"{d.metadata['url']}_{d.page_content[:50]}"
            ids.append(hashlib.md5(identifier.encode()).hexdigest())
        
        # add_documents with ids prevents the same chunk from being added twice
        vectorstore.add_documents(valid_docs, ids=ids)
        logger.info(f"Done! Added/updated {len(valid_docs)} chunks in ChromaDB.")
else:
    logger.warning("No documents found to index.")
