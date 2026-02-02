from dotenv import load_dotenv
import os
import json
import logging
import hashlib
from pathlib import Path
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter, Language
from langchain_core.documents import Document

load_dotenv() 
# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_local_markdown(folder_path):
    """
    Read all .md files from a local directory and convert them into Documents.
    
    Args:
        folder_path (str): Path to the directory containing Markdown files.
        
    Returns:
        list[Document]: List of processed documents.
    """
    documents = []
    data_path = Path(folder_path)
    
    if not data_path.exists():
        logger.error(f"Directory not found: {folder_path}")
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
                "language": "markdown" # Explicitly set to trigger markdown splitting logic
            }
            
            # Ensure all metadata values are strings for Chroma compatibility
            metadata = {k: str(v) for k, v in metadata.items() if v is not None}
            
            documents.append(Document(page_content=content, metadata=metadata))
            logger.info(f"Loaded: {file_path.name}")
            
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            
    return documents

# Configuration & Embeddings
# Keeping the same embedding model for consistency across agents
embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-m3")
persist_directory = "./planetix_comms.db"
source_folder = "./util/temp_comms_md"

# Initialize Chroma
vectorstore = Chroma(
    embedding_function=embeddings,
    persist_directory=persist_directory,
    collection_name="comms_docs"
)

# Splitter settings
# Using Language.MARKDOWN allows the splitter to respect headers and lists
splitter = RecursiveCharacterTextSplitter.from_language(
    language=Language.MARKDOWN,
    chunk_size=1000, 
    chunk_overlap=150
)

# Main Execution
logger.info(f"Starting local indexing from: {source_folder}")
all_documents = load_local_markdown(source_folder)

if all_documents:
    # Perform splitting
    split_docs = splitter.split_documents(all_documents)
    
    # Filter out very small chunks (junk/formatting artifacts)
    valid_docs = [d for d in split_docs if len(d.page_content.strip()) > 100]
    
    if valid_docs:
        # Create unique IDs based on content hash and source to prevent duplicates
        ids = []
        for d in valid_docs:
            # Combining URL and content snippet for a unique hash
            identifier = f"{d.metadata['url']}_{d.page_content[:100]}"
            ids.append(hashlib.md5(identifier.encode()).hexdigest())
        
        # Add to vectorstore using the calculated IDs (Upsert behavior)
        vectorstore.add_documents(valid_docs, ids=ids)
        logger.info(f"Success! Added/updated {len(valid_docs)} chunks in {persist_directory}.")
else:
    logger.warning("No Markdown documents were found or loaded.")
