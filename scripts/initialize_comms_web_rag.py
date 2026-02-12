"""
Initialize communications RAG database from web URLs.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ingestion.web_ingestor import WebIngestor

def main():
    script_dir = os.path.dirname(__file__)
    config_file = os.path.join(script_dir, '..', 'config', 'comms_documentation.json')
    persist_dir = os.path.join(script_dir, '..', 'planetix_comms.db')
    ingestor = WebIngestor(config_file, persist_directory=persist_dir)
    ingestor.run_ingestion()

if __name__ == "__main__":
    main()
