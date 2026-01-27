import os

# Set HuggingFace cache to project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
embedding_dir = os.path.join(project_root, 'embedding_model')
os.environ['HF_HOME'] = embedding_dir

import torch
from langchain_xai import ChatXAI
from langchain_huggingface import HuggingFaceEmbeddings

# --------------------------------------------------------- 
# ROCm PyTorch is not yet fully supported in Windows, so AMD
# will use the CPU only for now. Zz
#  ---------------------------------------------------------

# Automatically detect the best available device
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"✅  Embeddings running on: {device.upper()}")

# APU and GPU Architecture Detection
if device == "cuda":
    device_name = torch.cuda.get_device_name(0).lower()
    
    # Detect NVIDIA Grace Blackwell (DGX Spark / GB10)
    # Thanx Kristjan for letting me test on your box
    if 'gb10' in device_name or 'grace' in device_name:
        print(f"Detected NVIDIA Grace Blackwell APU: {device_name}")
        print("Optimizing for Coherent Unified Memory (128GB LPDDR5X)")
        # DGX Spark uses a shared memory pool; no need to restrict GPU memory growth
        # While torch will automatically handle VRAM allocation for non-DGX, the config DGX is explicit.
        torch.cuda.set_per_process_memory_fraction(1.0) 
        
    # Detect AMD APU/Discrete GPU
    elif 'amd' in device_name or 'radeon' in device_name:
        print(f"Detected AMD GPU: {device_name} - using ROCm")
    
    # Standard NVIDIA Discrete GPU
    else:
        print(f"Detected Discrete NVIDIA GPU: {device_name} - using CUDA")

# Configure the embedding model
model_name = "BAAI/bge-m3"
model_kwargs = {
    'device': device,
    'trust_remote_code': True
}

# If DGX Spark, change to 'batch_size': 515
encode_kwargs = {
    'normalize_embeddings': True,
    'batch_size': 32  
}

# Initialize the embeddings
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
