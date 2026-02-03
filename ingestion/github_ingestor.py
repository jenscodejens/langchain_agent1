import os
import json
import shutil
import stat
from pathlib import Path
from langchain_community.document_loaders import GitLoader
from langchain_core.documents import Document
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

    def load_documents(self) -> list[Document]:
        """Load documents from GitHub repositories."""
        documents = []
        temp_dirs = []

        for repo in self.github_repos:
            logger.info(f"Processing repository: {repo}")
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
                logger.info(f"\t{len(docs)} documents processed")

                for d in docs:
                    # Clean and stringify metadata for Chroma compatibility
                    d.metadata = {k: str(v) if v is not None else 'unknown' for k, v in d.metadata.items()}
                    # Explicitly set the repo name
                    d.metadata['repo'] = repo

                documents.extend(docs)
            except Exception as e:
                logger.error(f"Failed to load {repo}: {e}")

        # Cleanup temp directories
        for temp_dir in temp_dirs:
            if os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir, onexc=remove_readonly)
                except Exception as e:
                    logger.warning(f"Could not remove {temp_dir}: {e}")

        return documents

    def run_ingestion(self):
        """Override to add progress bar and check if DB exists."""
        if os.path.exists(self.persist_directory):
            logger.info(f"{self.persist_directory} already exists, skipping initialization")
            return

        logger.info(f"Starting GitHub ingestion for {len(self.github_repos)} repositories")
        documents = self.load_documents()
        if not documents:
            logger.warning("No documents loaded.")
            return

        split_docs = self.split_documents(documents)
        valid_docs = [d for d in split_docs if isinstance(d.page_content, str) and d.page_content.strip()]

        if valid_docs:
            ids = self.generate_ids(valid_docs)
            total_docs = len(valid_docs)
            batch_size = 100

            for i in range(0, total_docs, batch_size):
                batch = valid_docs[i:i+batch_size]
                self.save_to_vectorstore(batch, ids[i:i+batch_size])
                progress_bar(i + len(batch), total_docs)

            print("\r" + " " * 120 + "\r", end="")
            logger.info(f"GitHub ingestion complete: {total_docs} chunks in {self.persist_directory}")
        else:
            logger.warning("No valid documents to save.")