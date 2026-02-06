import os
import json
import shutil
import stat
import hashlib
import requests
import time
from pathlib import Path
from langchain_community.document_loaders import GitLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter, Language
from .base_ingestor import BaseIngestor
from util.progress import progress_bar
import logging

logger = logging.getLogger(__name__)

def advanced_file_filter(file_path):
    """Filter files based on extensions and special names, excluding junk directories."""
    filename = os.path.basename(file_path).lower()

    # Ignore common junk directories
    ignored_parts = {'.git', 'node_modules', '__pycache__', 'dist', 'build', 'venv', '.env'}
    if any(part in file_path.split(os.sep) for part in ignored_parts):
        return False

    # Special architecture/config files
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

class GitHubIngestor(BaseIngestor):
    def __init__(self, config_path: str, persist_directory: str = "./github.db", collection_name: str = "github_repos"):
        super().__init__(persist_directory, collection_name)
        with open(config_path, 'r') as f:
            config = json.load(f)
        self.github_repos = config['github_repos']
        self.temp_dirs = []

    def generate_ids(self, documents: list[Document]) -> list[str]:
        """Generate unique IDs for documents, including repo for uniqueness."""
        ids = []
        for doc in documents:
            # Extract repo and source from metadata for uniqueness across repositories
            repo = doc.metadata.get('repo', '')
            source = doc.metadata.get('source', '')
            # Create a hash of the full document content to detect changes
            content_hash = hashlib.md5(doc.page_content.encode()).hexdigest()
            # Combine repo, source, and content hash into a unique identifier
            identifier = f"{repo}_{source}_{content_hash}"
            # Generate an MD5 hash of the identifier for a consistent ID
            ids.append(hashlib.md5(identifier.encode()).hexdigest())
        return ids

    def split_documents(self, documents: list[Document]) -> list[Document]:
        """Split documents using language-aware splitting with custom chunk size and overlap."""
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

            # Override default. Major tweak tool
            language = ext_to_language.get(ext)
            if language:
                splitter = RecursiveCharacterTextSplitter.from_language(
                    language=language,
                    chunk_size=800,
                    chunk_overlap=100,
                )
            else:
                splitter = RecursiveCharacterTextSplitter(
                    chunk_size=800,
                    chunk_overlap=100,
                )
            chunks = splitter.split_documents([doc])
            split_docs.extend(chunks)

        return split_docs

    def load_documents(self) -> list[Document]:
        """Load documents from GitHub repositories."""
        documents = []

        for repo in self.github_repos:
            print(f"Processing repository: {repo}")
            safe_repo_name = repo.replace('/', '_').replace('\\', '_')
            temp_dir = os.path.abspath(f"./temp_{safe_repo_name}")
            self.temp_dirs.append(temp_dir)

            try:
                # Get the default branch from GitHub API
                api_url = f"https://api.github.com/repos/{repo}"
                response = requests.get(api_url)
                response.raise_for_status()
                repo_data = response.json()
                default_branch = repo_data['default_branch']
                print(f"\tDefault branch: {default_branch}, Size: {repo_data.get('size', 'unknown')} KB")

                loader = GitLoader(
                    repo_path=temp_dir,
                    clone_url=f"https://github.com/{repo}.git",
                    branch=default_branch,
                    file_filter=advanced_file_filter
                )
                docs = loader.load()

                # Count total files in repo and list some
                matching_files = []
                for root, dirs, files in os.walk(temp_dir):
                    if not any(ignored in root for ignored in ['.git', 'node_modules', '__pycache__', 'dist', 'build', 'venv', '.env']):
                        for f in files:
                            full_path = os.path.join(root, f)
                            if advanced_file_filter(full_path):
                                matching_files.append(full_path)
                total_files = len(matching_files)
                print(f"\tTotal filter-matching files: {total_files}, Documents loaded: {len(docs)}")
                if total_files > 0 and len(docs) == 0:
                    print(f"\tSample matching files: {matching_files[:5]}")  # Show first 5
                    # Try to read a sample file
                    try:
                        with open(matching_files[0], 'r', encoding='utf-8') as f:
                            content = f.read()
                            print(f"\tSample file '{os.path.basename(matching_files[0])}' content length: {len(content)}")
                    except Exception as e:
                        print(f"\tError reading sample file: {e}")

                print(f"\t{len(docs)} documents processed")

                for d in docs:
                    # Clean and stringify metadata for Chroma compatibility
                    d.metadata = {k: str(v) if v is not None else 'unknown' for k, v in d.metadata.items()}
                    # Explicitly set the repo name
                    d.metadata['repo'] = repo

                documents.extend(docs)
            except Exception as e:
                print(f"Failed to load {repo}: {e}")

        return documents

    def run_ingestion(self):
        """Override to add progress bar and check if DB exists."""
        # if os.path.exists(self.persist_directory):
        #     print(f"{self.persist_directory} already exists, skipping initialization")
        #     return

        print(f"Starting GitHub ingestion for {len(self.github_repos)} repositories")
        documents = self.load_documents()
        if not documents:
            print("No documents loaded.")
            return

        split_docs = self.split_documents(documents)
        valid_docs = [d for d in split_docs if isinstance(d.page_content, str) and d.page_content.strip()]

        if valid_docs:
            ids = self.generate_ids(valid_docs)
            total_docs = len(valid_docs)
            batch_size = 100

            try:
                for i in range(0, total_docs, batch_size):
                    batch = valid_docs[i:i+batch_size]
                    self.save_to_vectorstore(batch, ids[i:i+batch_size])
                    progress_bar(i + len(batch), total_docs)
            except KeyboardInterrupt:
                print("\nIngestion interrupted by user. Partial progress saved.")
                return

            print("\r" + " " * 120 + "\r", end="")
            logger.info(f"GitHub ingestion complete: {total_docs} chunks in {self.persist_directory}")
        else:
            logger.warning("No valid documents to save.")

        # Cleanup temp directories after all processing
        for temp_dir in self.temp_dirs:
            if os.path.exists(temp_dir):
                for attempt in range(3):
                    try:
                        time.sleep(2 * (attempt + 1))  # Increasing delay: 2s, 4s, 6s
                        shutil.rmtree(temp_dir, onexc=remove_readonly)
                        break  # Success, exit retry loop
                    except Exception as e:
                        if attempt == 2:  # Last attempt
                            print(f"Could not remove {temp_dir} after 3 attempts: {e}")
                        else:
                            print(f"Attempt {attempt + 1} failed for {temp_dir}, retrying...")