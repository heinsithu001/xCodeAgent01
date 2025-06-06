# Enhanced CodeAgent Backend v2.0 Dockerfile
# Production-ready container with vLLM integration

FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    wget \
    lsof \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd --create-home --shell /bin/bash app
WORKDIR /app
RUN chown app:app /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install vLLM (CPU version for broader compatibility)
RUN pip install --no-cache-dir vllm

# Copy application code
COPY --chown=app:app . .

# Create necessary directories
RUN mkdir -p logs workspace models cache temp && \
    chown -R app:app logs workspace models cache temp

# Switch to app user
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:12000/api/v2/status || exit 1

# Expose port
EXPOSE 12000

# Default command
CMD ["python", "main.py"]