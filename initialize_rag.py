import os
import json
import shutil
import stat
import time
from dotenv import load_dotenv
from langchain_community.document_loaders import GitLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter, Language
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from pygments.lexers import guess_lexer
from pygments.util import ClassNotFound
from util.progress import progress_bar

load_dotenv()

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
    """Remove read-only attribute and retry the operation (Windows fix)."""
    os.chmod(path, stat.S_IWRITE)
    func(path)

# Load config
with open('config/github_repositories.json', 'r') as f:
    config = json.load(f)

github_repos = config['github_repos']
persist_directory = "./github.db"

# Check if ChromaDB exists
if os.path.exists(persist_directory):
    print(f"ℹ  {persist_directory} already exists, skipping initialization")
    exit(0)

# Initialize Embeddings
embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-m3")

documents = []
temp_dirs = []

print()
for repo in github_repos:
    print(f"Processing repository: {repo}")
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
        print(f"\t{len(docs)} documents processed")
        for d in docs:
            d.metadata['repo'] = repo
        documents.extend(docs)
    except Exception as e:
        print(f"Failed to load {repo}: {e}")

print(f"\n✅ Completed {len(github_repos)} repositories with a total of {len(documents)} documents")

# --- CORRECTED: Dynamic language-aware splitting ---
# Dynamic language-aware splitting - Only including supported LangChain enums
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
    ".html": Language.HTML,
    # Språk som SQL, YAML, JSON, Dart, Bash saknar specifika enums i denna version
    # och kommer automatiskt falla tillbaka på RecursiveCharacterTextSplitter (plain text)
}

# Split documents
split_docs = []
for doc in documents:
    source_path = doc.metadata.get("source", "")
    _, ext = os.path.splitext(source_path)
    # Fallback to Language.PYTHON or PLAIN if not found
    language = ext_to_language.get(ext.lower())
    
    try:
        if language:
            splitter = RecursiveCharacterTextSplitter.from_language(
                language=language,
                chunk_size=1500,
                chunk_overlap=150,
            )
        else:
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=1500,
                chunk_overlap=150,
            )
        chunks = splitter.split_documents([doc])
        split_docs.extend(chunks)
    except Exception as e:
        # Silently skip errors for unsupported languages in certain LangChain versions
        continue

print(f"\tSplit into {len(split_docs)} chunks")

# Filter out invalid documents
split_docs = [doc for doc in split_docs if isinstance(doc.page_content, str) and doc.page_content.strip()]
print(f"\tFiltered to {len(split_docs)} valid chunks\n")

# Add language metadata using Pygments
for doc in split_docs:
    try:
        lexer = guess_lexer(doc.page_content)
        doc.metadata['language_name'] = lexer.name
    except ClassNotFound:
        doc.metadata['language_name'] = 'unknown'

# --- CORRECTED: Create Chroma vectorstore ---
total_docs = len(split_docs)
batch_size = 100 # Safe batch size for Windows/SQLite
vectorstore = None

for i in range(0, total_docs, batch_size):
    batch = split_docs[i:i+batch_size]
    if vectorstore is None:
        vectorstore = Chroma.from_documents(
            documents=batch,
            embedding=embeddings, # Correct param for 0.1.x
            persist_directory=persist_directory,
            collection_name="github_repos"
        )
    else:
        vectorstore.add_documents(batch)
    progress_bar(i + len(batch), total_docs)

print("\r" + " " * 120 + "\r", end="")
print(f"✅ {persist_directory} initialized and populated")

# Cleanup temp directories
for temp_dir in temp_dirs:
    if os.path.exists(temp_dir):
        try:
            time.sleep(0.5) # Give Git time to release files
            shutil.rmtree(temp_dir, onexc=remove_readonly)
        except Exception as e:
            print(f"⚠️ Warning: Could not remove {temp_dir}: {e}")

print(f"✅ Initialization complete.")
