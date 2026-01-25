import os
import torch
from langchain_xai import ChatXAI
from langchain_huggingface import HuggingFaceEmbeddings

# Set HuggingFace cache to project root
os.environ['HF_HOME'] = './embedding_model'

# 1. Automatically detect the best available device (NVIDIA or AMD)
# AMD (ROCm) shares the 'cuda' naming convention with NVIDIA in PyTorch
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Embeddings running on: {device.upper()}")

# 2. Configure the embedding model
model_name = "BAAI/bge-m3"
model_kwargs = {'device': device}
encode_kwargs = {'normalize_embeddings': False}

# 3. Initialize the embeddings
embeddings = HuggingFaceEmbeddings(
    model_name=model_name,
    model_kwargs=model_kwargs,
    encode_kwargs=encode_kwargs
)

# LLM Configuration
llm_model = ChatXAI(
    model="grok-4-1-fast-reasoning",
    temperature=0,
    streaming=True,
    timeout=60,
    max_retries=2,
    verbose=True
)