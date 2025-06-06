# Enhanced CodeAgent Integration Dockerfile
# Multi-stage build for optimized container size

# Base stage with common dependencies
FROM python:3.12-slim as base

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

# Switch to app user
USER app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# Development stage
FROM base as development

# Copy source code
COPY --chown=app:app . .

# Install development dependencies
RUN pip install --user pytest pytest-asyncio black flake8 mypy

# Expose ports
EXPOSE 8000 12000

# Default command
CMD ["./scripts/start.sh", "--daemon"]

# Production stage
FROM base as production

# Copy only necessary files
COPY --chown=app:app src/ ./src/
COPY --chown=app:app scripts/ ./scripts/
COPY --chown=app:app config/ ./config/
COPY --chown=app:app requirements.txt .

# Make scripts executable
RUN chmod +x scripts/*.sh

# Create necessary directories
RUN mkdir -p logs workspace models cache temp

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:12000/health || exit 1

# Expose ports
EXPOSE 8000 12000

# Default command
CMD ["./scripts/start.sh", "--daemon"]