FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency files first
COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/

# Install pip and then install CPU-only PyTorch and other dependencies
RUN pip install --upgrade pip && \
    pip install torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install transformers pydantic fastapi uvicorn && \
    pip install -e .

# Don't pre-download the model - it will be downloaded on first startup
# This reduces Docker image size to stay under Fly.io's 8GB limit

# Set environment
ENV PYTHONPATH=/app/src \
    TRANSFORMERS_CACHE=/app/.cache \
    API_HOST=0.0.0.0 \
    API_PORT=8002 \
    UVICORN_WORKERS=2 \
    LOG_LEVEL=info

# Expose port
EXPOSE 8002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# Run the application (uses config for workers)
CMD ["python", "-m", "benz_sent_filter"]