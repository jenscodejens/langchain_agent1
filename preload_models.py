#!/usr/bin/env python3
"""
Pre-download Hugging Face models to cache them locally and reduce startup time.
Run this script before starting the app to avoid downloads during runtime.
"""

import os
from huggingface_hub import snapshot_download

# Set the cache directory to match llm_config.py
project_root = os.path.dirname(os.path.abspath(__file__))
embedding_dir = os.path.join(project_root, 'embedding_model')
os.environ['HF_HOME'] = embedding_dir

print("Pre-downloading BAAI/bge-m3...")
snapshot_download(repo_id="BAAI/bge-m3", local_dir=os.path.join(embedding_dir, "models--BAAI--bge-m3"))

print("Pre-downloading BAAI/bge-reranker-v2-m3...")
snapshot_download(repo_id="BAAI/bge-reranker-v2-m3", local_dir=os.path.join(embedding_dir, "models--BAAI--bge-reranker-v2-m3"))

print("Model pre-download complete.")