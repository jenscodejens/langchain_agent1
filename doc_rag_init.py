import json
import logging
import os
import re
from dateutil import parser as date_parser
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
# Use this to split text based on units (sentences/paragraphs), use CharacterTextSplitter for strict length
from langchain_text_splitters import RecursiveCharacterTextSplitter

import trafilatura
from langchain_core.documents import Document

def clean_text(text):
    # Clean and normalize whitespace in the text
    return re.sub(r'\s+', ' ', text).strip()

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def indexing_pipeline(url):
    try:
        downloaded = trafilatura.fetch_url(url)
        text = trafilatura.extract(downloaded)
        cleaned_text = clean_text(text) if text else ""
        if cleaned_text.strip():
            doc = Document(page_content=cleaned_text, metadata={})
            return [doc]
        return []
    except Exception as e:
        logger.error(f"Error processing {url}: {e}")
        return []

# Configuration & Embeddings
with open('config/comms.json', 'r') as f:
    config = json.load(f)

embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-m3")
persist_directory = "./chroma_doc_db"

# Initialize Chroma
vectorstore = Chroma(
    embedding_function=embeddings,
    persist_directory=persist_directory,
    collection_name="comms_docs"
)

splitter = RecursiveCharacterTextSplitter(
    chunk_size=300,       # Approximate length for 3 sentences
    chunk_overlap=50,     # Overlap for context
    separators=["\n\n", "\n", ". ", " ", ""] 
)

documents = []
for url in config.get('comms_docs', []):
    logger.info(f"Processing URL: {url}")
    docs = indexing_pipeline(url)
    
    for doc in docs:
        # Trafilatura already cleans, but normalize whitespace
        doc.page_content = clean_text(doc.page_content)
        # Extract publish date only if at start
        date_regex = r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2}|\w+ \d{1,2}, \d{4})\b'
        match = re.search(date_regex, doc.page_content)
        publish_date = None
        pos = None
        if match and match.start() < 300:
            try:
                publish_date = date_parser.parse(match.group(1)).isoformat()
                pos = match.start()
                doc.metadata['publish_date'] = publish_date
            except ValueError:
                pass
        logger.info(f"URL: {url} - Publish date: {publish_date} (pos: {pos})")
        
        doc.metadata['url'] = url
        documents.append(doc)

# Split and Save
if documents:
    # split_documents handles the list directly
    split_docs = splitter.split_documents(documents)
    
    # Filter out empty documents
    valid_docs = [d for d in split_docs if d.page_content.strip()]
    
    if valid_docs:
        vectorstore.add_documents(valid_docs)
        logger.info(f"Added {len(valid_docs)} chunks to ChromaDB")
