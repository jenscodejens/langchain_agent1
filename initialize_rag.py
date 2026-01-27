import os
import json
import shutil
import stat
import time
from langchain_community.document_loaders import GitLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from pygments.lexers import guess_lexer
from pygments.util import ClassNotFound
from util.progress import progress_bar

def advanced_file_filter(file_path):
    """Filter files based on extensions and special names, excluding junk directories."""
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

def remove_readonly(func, path, excinfo):
    """Remove read-only attribute and retry the operation."""
    try:
        os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)  # chmod 0777
        func(path)
    except OSError:
        pass  # Ignore if we can't change permissions

# Load config
with open('config/github_repositories.json', 'r') as f:
    config = json.load(f)

github_repos = config['github_repos']
persist_directory = "./chroma_db"

# Check if ChromaDB exists
if os.path.exists(persist_directory):
    print(f"\U00002139  ChromaDB already exists, skipping initialization")
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
temp_dirs = []

for repo in github_repos:
    print(f"Loading repo: {repo}")
    # Sanitize repo name for folder paths
    safe_repo_name = repo.replace('/', '_').replace('\\', '_')
    temp_dir = f"./temp_{safe_repo_name}"
    temp_dirs.append(temp_dir)
    
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

print(f"Loaded {len(documents)} total documents")

# Split documents
split_docs = text_splitter.split_documents(documents)
print(f"\nSplit into {len(split_docs)} chunks")

# Filter out invalid documents (non-strings, whitespace etc)
split_docs = [doc for doc in split_docs if isinstance(doc.page_content, str) and doc.page_content.strip()]
print(f"Filtered to {len(split_docs)} valid chunks\n")

# Add language metadata using Pygments
for doc in split_docs:
    try:
        lexer = guess_lexer(doc.page_content)
        doc.metadata['language'] = lexer.name
    except ClassNotFound:
        doc.metadata['language'] = 'unknown'

# Create Chroma vectorstore (persist)
total_docs = len(split_docs)
batch_size = max(1, total_docs // 100)
vectorstore = None
for i in range(0, total_docs, batch_size):
    batch = split_docs[i:i+batch_size]
    if vectorstore is None:
        vectorstore = Chroma.from_documents(
            documents=batch,
            embedding=embeddings,
            persist_directory=persist_directory,
            collection_name="github_repos"
        )
    else:
        vectorstore.add_documents(batch)
    progress_bar(i + len(batch), total_docs)

print("\r" + " " * 120 + "\r", end="")  # Clear the ugly progress bar after completion
print("\U00002705  ChromaDB initialized and populated")

# Cleanup temp directories, small delay needed for Git to release the lock on those folders
cleanup_success = True
for temp_dir in temp_dirs:
    if os.path.exists(temp_dir):
        try:
            time.sleep(0.2)
            shutil.rmtree(temp_dir, onexc=remove_readonly)
        except Exception as e:
            print(f"\U000026A0  Warning: Failed to remove temp directory {temp_dir}: {e}")
            cleanup_success = False

if cleanup_success:
    print(f"\U00002705  Cleanup of temp folders performed")
else:
    print(f"\U000026A0  Cleanup of temp folders completed with warnings")
