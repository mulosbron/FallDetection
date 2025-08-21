# Multi-stage build için base image
FROM nvidia/cuda:12.1.1-devel-ubuntu22.04 AS base

# System dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-dev \
    python3-venv \
    python3-pip \
    git \
    curl \
    wget \
    build-essential \
    libssl-dev \
    libffi-dev \
    libjpeg-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# Varsayılan python3 zaten kurulu (Ubuntu 22.04'te 3.10). Ek ayara gerek yok.

# Pip güncelle
RUN python3 -m pip install --upgrade pip setuptools wheel

# Production stage
FROM base AS production

# Working directory
WORKDIR /app

# Environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV TRANSFORMERS_CACHE=/app/.cache/transformers
ENV HF_HOME=/app/.cache/huggingface

# Cache directories oluştur
RUN mkdir -p /app/.cache/transformers /app/.cache/huggingface /app/logs

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies (PyPI ana index, PyTorch ek index)
RUN pip install --no-cache-dir \
    --index-url https://pypi.org/simple \
    --extra-index-url https://download.pytorch.org/whl/cu121 \
    -r requirements.txt

# Copy application code
COPY main.py .
COPY model_service.py .
COPY database.py .

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Start command
CMD ["python3", "main.py"]
