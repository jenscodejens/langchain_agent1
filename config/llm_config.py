import torch
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_xai import ChatXAI

# AMD ROCm is not fully implemented for Win yet, will run on CPU
if torch.backends.mps.is_available():
    device = "mps"
elif torch.cuda.is_available():
    device = "cuda"
else:
    device = "cpu"

print(f"Använder device: {device}")

model_name = "BAAI/bge-m3"
model_kwargs = {
    'device': device,
    'trust_remote_code': True
}

encode_kwargs = {
    'normalize_embeddings': True,
    'batch_size': 64
}

# Initialize embeddings
embeddings = HuggingFaceEmbeddings(
    model_name=model_name,
    model_kwargs=model_kwargs,
    encode_kwargs=encode_kwargs
)

# LLM Configuration (Grok)
llm_model = ChatXAI(
    model="grok-4-1-fast-reasoning",
    temperature=0,
    streaming=True,
    timeout=60,
    max_retries=2,
    verbose=True
)
