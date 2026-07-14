# =========================================================
# Finanza Banking API — Production Dockerfile
# Multi-stage build: slim runtime image for deployment
# =========================================================

# --- Stage 1: Builder (install dependencies) ---
FROM python:3.11-slim AS builder

# Install OS-level build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first to leverage Docker layer caching
COPY requirements.txt .

# Install Python dependencies into a prefix (for easy copy to final stage)
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt


# --- Stage 2: Runtime (lean final image) ---
FROM python:3.11-slim AS runtime

LABEL maintainer="Finanza Bank <dev@finanzabank.com>"
LABEL description="Finanza Banking Platform API"

# Install minimal runtime OS deps (libpq for asyncpg, libssl for TLS)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libssl3 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

WORKDIR /app

# Create non-root user for security
RUN groupadd -r finanza && useradd -r -g finanza -s /bin/false finanza

# Copy application source code
COPY . .

# Create uploads directory (writable by app user)
RUN mkdir -p uploads && chown -R finanza:finanza /app

# Drop to non-root user
USER finanza

# Expose application port
EXPOSE 8000

# Health check — calls the public /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start the application with production settings
# - workers: 2 per core (adjust based on instance size)
# - timeout-keep-alive: 65s (above typical ALB 60s idle timeout)
CMD ["uvicorn", "main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2", \
     "--timeout-keep-alive", "65", \
     "--access-log", \
     "--no-use-colors"]
