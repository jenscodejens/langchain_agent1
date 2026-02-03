#!/usr/bin/env python3
"""
Initialize GitHub RAG database from configured repositories.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ingestion.github_ingestor import GitHubIngestor

def main():
    script_dir = os.path.dirname(__file__)
    config_file = os.path.join(script_dir, '..', 'config', 'github_repositories.json')
    persist_dir = os.path.join(script_dir, '..', 'github.db')
    ingestor = GitHubIngestor(config_file, persist_directory=persist_dir)
    ingestor.run_ingestion()

if __name__ == "__main__":
    main()
