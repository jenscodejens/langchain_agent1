import os
import json
import shutil
from langchain_community.document_loaders import GitLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from pygments.lexers import guess_lexer
from pygments.util import ClassNotFound

def advanced_file_filter(file_path):
    filename = os.path.basename(file_path).lower()
    
    # Ignore common junk directories
    ignored_parts = {'.git', 'node_modules', '__pycache__', 'dist', 'build', 'venv', '.env'}
    if any(part in file_path.split(os.sep) for part in ignored_parts):
        return False

    # Special architecture/config files (no extensions or specific names)
    special_names = [
        'dockerfile', 'makefile', 'procfile', 'jenkinsfile', 
        'vagrantfile', 'gemfile', 'rakefile', 'cargo.lock', 
        'go.mod', 'go.sum', 'pyproject.toml', 'package.json'
    ]
    if any(filename.startswith(name) for name in special_names):
        return True

    # Language support
    valid_extensions = [
        '.py', '.pyi', '.ipynb', '.js', '.jsx', '.ts', '.tsx', 
        '.java', '.kt', '.kts', '.rs', '.go', '.c', '.cpp', 
        '.h', '.hpp', '.cs', '.swift', '.dart', '.php', '.rb', 
        '.sh', '.bash', '.zsh', '.ps1', '.sql', '.r', '.md', 
        '.markdown', '.rst', '.adoc', '.txt', '.json', '.yaml', 
        '.yml', '.toml', '.xml', '.env', '.ini'
    ]
    return any(filename.endswith(ext) for ext in valid_extensions)

# Load config
with open('config.json', 'r') as f:
    config = json.load(f)

github_repos = config['github_repos']
persist_directory = "./chroma_db"

# Check if ChromaDB exists
if os.path.exists(persist_directory):
    print("ChromaDB already exists. Skipping initialization.")
    exit(0)

# Initialize Embeddings
embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-m3")

# Text splitter
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len,
)

documents = []

for repo in github_repos:
    print(f"Loading repo: {repo}")
    # Sanitize repo name for folder paths
    safe_repo_name = repo.replace('/', '_').replace('\\', '_')
    temp_dir = f"./temp_{safe_repo_name}"
    
    try:
        loader = GitLoader(
            repo_path=temp_dir,
            clone_url=f"https://github.com/{repo}.git",
            branch="main",
            file_filter=advanced_file_filter
        )
        docs = loader.load()
        # Add source repo to metadata
        for d in docs:
            d.metadata['repo'] = repo
        documents.extend(docs)
    except Exception as e:
        print(f"Failed to load {repo}: {e}")
    finally:
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                print(f"Warning: Failed to remove temp directory {temp_dir}: {e}")

print(f"Loaded {len(documents)} total documents")

# Split documents
split_docs = text_splitter.split_documents(documents)
print(f"Split into {len(split_docs)} chunks")

# Filter out invalid documents
split_docs = [doc for doc in split_docs if isinstance(doc.page_content, str) and doc.page_content.strip()]
print(f"Filtered to {len(split_docs)} valid chunks")

# Add language metadata using Pygments
for doc in split_docs:
    try:
        lexer = guess_lexer(doc.page_content)
        doc.metadata['language'] = lexer.name
    except ClassNotFound:
        doc.metadata['language'] = 'unknown'

# Create Chroma vectorstore (persist)
vectorstore = Chroma.from_documents(
    documents=split_docs,
    embedding=embeddings,
    persist_directory=persist_directory,
    collection_name="github_repos"
)

print("ChromaDB initialized and populated with 2026 standards.")
