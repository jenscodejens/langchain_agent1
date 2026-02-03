#!/usr/bin/env python3
"""
Initialize communications RAG database from local Markdown files.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ingestion.local_md_ingestor import LocalMDIngestor

def main():
    script_dir = os.path.dirname(__file__)
    data_dir = os.path.join(script_dir, '..', 'data', 'comms_pages_as_md')
    persist_dir = os.path.join(script_dir, '..', 'planetix_comms.db')
    ingestor = LocalMDIngestor(data_dir, persist_directory=persist_dir)
    ingestor.run_ingestion()

if __name__ == "__main__":
    main()
