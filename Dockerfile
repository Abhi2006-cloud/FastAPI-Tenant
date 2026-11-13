# Multi-stage production Dockerfile for FastAPI API & RQ Background Worker

# Stage 1: Build stage
FROM python:3.12-slim AS builder

WORKDIR /build

# Install system build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies into wheels
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Final runtime image
FROM python:3.12-slim AS runner

WORKDIR /app

# Install runtime system packages (libpq for psycopg2) and curl for health check
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy python packages from builder stage
COPY --from=builder /install /usr/local

# Create non-root user and directories
RUN groupadd -r appgroup && useradd -r -g appgroup -d /app -s /sbin/nologin appuser \
    && mkdir -p /app/uploads \
    && chown -R appuser:appgroup /app

# Copy application source code
COPY app/ ./app/
COPY templates/ ./templates/
COPY alembic/ ./alembic/
COPY alembic.ini .
COPY VERSION .

# Switch to non-root user
USER appuser

# Environment defaults
ENV PORT=8000 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://127.0.0.1:${PORT}/health || exit 1

# Default command: single gunicorn worker with embedded RQ worker and migrations on startup
CMD ["sh", "-c", "alembic upgrade head && gunicorn -w ${WEB_CONCURRENCY:-1} -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:${PORT} --timeout 120"]
