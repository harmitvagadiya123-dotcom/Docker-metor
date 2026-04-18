# ============================================================
# LinkedIn Authority Mentor — Optimized Docker Image
# Target: < 200MB compressed
# ============================================================

# ── Stage 1: Builder ─────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies (needed for some pip packages)
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: Runtime ─────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Labels
LABEL maintainer="Nannathi Group"
LABEL description="LinkedIn Authority Mentor — Agentic AI for LinkedIn Content Posting"
LABEL version="1.0.0"

# Security: run as non-root user
RUN groupadd -r mentor && useradd -r -g mentor -d /app -s /sbin/nologin mentor

WORKDIR /app

# Copy only the installed packages from builder (no build tools)
COPY --from=builder /install /usr/local

# Copy application source
COPY src/ ./src/

# Set ownership
RUN chown -R mentor:mentor /app

# Switch to non-root user
USER mentor

# Environment defaults
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LOG_LEVEL=INFO \
    PORT=10000

EXPOSE 10000

# Health check: verify Python and dependencies load
HEALTHCHECK --interval=60s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from src.config.settings import Settings; print('OK')" || exit 1

# Default: run with scheduler
ENTRYPOINT ["python", "-m", "src.main"]

# Can be overridden: --run-now, --verify
CMD []
