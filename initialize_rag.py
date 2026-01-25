import os
import json
import shutil
from langchain_community.document_loaders import GitLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from pygments.lexers import guess_lexer
from pygments.util import ClassNotFound

# Load config
with open('config.json', 'r') as f:
    config = json.load(f)

github_repos = config['github_repos']

# Embeddings
from langchain_huggingface import HuggingFaceEmbeddings
embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-m3")

# Check if ChromaDB exists
persist_directory = "./chroma_db"
if os.path.exists(persist_directory):
    print("ChromaDB already exists. Skipping initialization.")
    exit(0)

# Text splitter
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len,
)

documents = []

for repo in github_repos:
    print(f"Loading repo: {repo}")
    temp_dir = f"./temp_{repo.replace('/', '_')}"
    try:
        loader = GitLoader(
            repo_path=temp_dir,
            clone_url=f"https://github.com/{repo}.git",
            branch="main",
            file_filter=lambda file_path: any(file_path.endswith(ext) for ext in ['.py', '.js', '.ts', '.md', '.txt', '.json', '.yaml', '.yml'])
        )
        docs = loader.load()
        documents.extend(docs)
    except Exception as e:
        print(f"Failed to load {repo}: {e}")
    finally:
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                print(f"Warning: Failed to remove temp directory {temp_dir}: {e}")

print(f"Loaded {len(documents)} documents")

# Split documents
split_docs = text_splitter.split_documents(documents)

print(f"Split into {len(split_docs)} chunks")

# Filter out invalid documents
split_docs = [doc for doc in split_docs if isinstance(doc.page_content, str) and doc.page_content.strip()]

print(f"Filtered to {len(split_docs)} valid chunks")

# Add language metadata
for doc in split_docs:
    try:
        lexer = guess_lexer(doc.page_content)
        doc.metadata['language'] = lexer.name
    except ClassNotFound:
        doc.metadata['language'] = 'unknown'

# Create Chroma vectorstore
vectorstore = Chroma.from_documents(
    documents=split_docs,
    embedding=embeddings,
    persist_directory=persist_directory,
    collection_name="github_repos"
)

print("ChromaDB initialized and populated.")