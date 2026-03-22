# RunPod Serverless Dockerfile for audio processing
# Base image with CUDA
FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

LABEL maintainer="sapirl7"
LABEL description="Callsum ML Service - Audio transcription, diarization, and summarization"

# Disable interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    ffmpeg \
    libsndfile1 \
    git \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Create working directory
WORKDIR /app

# Create model cache directories
RUN mkdir -p /models/whisper /models/pyannote /models/llama

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir -r requirements.txt

# Copy application code
COPY handler.py .

# Preload models to reduce cold start time
# (optional — increases image size but speeds up startup)
ARG PRELOAD_MODELS=true
ARG HF_TOKEN

RUN if [ "$PRELOAD_MODELS" = "true" ]; then \
    echo "Preloading models..."; \
    # Whisper large-v3 (~3GB)
    python3 -c "from faster_whisper import WhisperModel; WhisperModel('large-v3', device='cpu', download_root='/models/whisper')"; \
    # Llama 3.1-8B-Instruct (~5GB) — saves 1-3 minutes on cold start
    pip3 install --no-cache-dir huggingface_hub && \
    python3 -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='meta-llama/Meta-Llama-3.1-8B-Instruct', cache_dir='/models/llama', token='${HF_TOKEN}') if '${HF_TOKEN}' else print('Warning: HF_TOKEN not set, skipping Llama download')"; \
    fi

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV HF_HOME=/models
ENV TRANSFORMERS_CACHE=/models
ENV TORCH_HOME=/models

# Create non-root user for runtime
RUN groupadd -r appuser && useradd -r -g appuser -d /app appuser && \
    chown -R appuser:appuser /app /models
USER appuser

# Expose port (for local testing)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python3 -c "import torch; print(torch.cuda.is_available())" || exit 1

# RunPod serverless handler
CMD ["python3", "-u", "handler.py"]
