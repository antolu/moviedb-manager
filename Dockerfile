# syntax=docker/dockerfile:1.4
ARG BUILD_TYPE=production

# --- Stage 1: Build the React frontend ---
FROM node:22-alpine AS frontend-builder
WORKDIR /build

# Install dependencies
COPY frontend/package*.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci

# Copy source and build
COPY frontend/ ./
RUN npm run build

# --- Stage 2: Python Base ---
FROM python:3.14-slim AS base
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install common system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r moviedb && useradd -r -g moviedb moviedb

WORKDIR /app

# --- Stage 3: Development ---
FROM base AS development
# Install watchfiles for hot reloading
RUN pip install --no-cache-dir watchfiles

# Copy configuration files
COPY pyproject.toml README.md ./
COPY moviedb_manager/ ./moviedb_manager/

# Install dependencies (including dev/test)
# Mount .git for setuptools-scm to work during installation
RUN --mount=type=bind,source=.git,target=/app/.git \
    --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -e ".[dev,test]"

# Copy and set up entrypoint
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Switch to non-root user
USER moviedb

# Expose port
EXPOSE 5000

ENTRYPOINT ["/docker-entrypoint.sh"]

# Default command for development (overridden in compose)
CMD ["uvicorn", "moviedb_manager.app:app", "--host", "0.0.0.0", "--port", "5000", "--reload"]

# --- Stage 4: Production ---
FROM base AS production

# Copy built frontend assets
COPY --from=frontend-builder /build/frontend/dist ./moviedb_manager/static

# Copy application code
COPY moviedb_manager/ ./moviedb_manager/
COPY pyproject.toml README.md ./

# Install the package itself with git context for proper setuptools-scm versioning
RUN --mount=type=bind,source=.git,target=/app/.git \
    --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir .

# Copy and set up entrypoint
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Create data directory
RUN mkdir -p /app/data && chown moviedb:moviedb /app/data

# Switch to non-root user
USER moviedb

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/api/status')" || exit 1

ENTRYPOINT ["/docker-entrypoint.sh"]

# Command to run the application
CMD ["python", "-m", "moviedb_manager.app"]

# --- Final Stage ---
FROM ${BUILD_TYPE} AS final
