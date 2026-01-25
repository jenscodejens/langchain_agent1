# Use Python 3.13 slim image (matches your pyproject.toml requirement)
FROM python:3.13-slim

# Metadata labels
LABEL maintainer="not_yet@example.com"
LABEL version="0.5b"
LABEL description="Agentic LangChain-based RAG application"

# Set working directory
WORKDIR /app

# Install system dependencies if needed (e.g., for some LangChain tools)
# RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

# Copy dependency files first (for better caching)
COPY requirements.txt .
COPY pyproject.toml .

# Install Python dependencies using uv for faster installs
RUN pip install uv && uv pip install --system --no-cache -r requirements.txt && uv cache clean

# Create non-root user
RUN useradd --create-home --shell /bin/bash app

# Copy the rest of the source code with ownership
COPY --chown=app:app . .

# Switch to non-root user
USER app

# Expose the port Chainlit runs on
EXPOSE 8000

# Command to run the app
CMD ["python", "backend/run_chainlit.py"]