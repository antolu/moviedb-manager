# Stage 1: Build the React frontend
FROM node:22-alpine AS frontend-builder
WORKDIR /build

RUN apk add --no-cache git python3 py3-pip

COPY pyproject.toml ./
COPY moviedb_manager/ ./moviedb_manager/
COPY .git/ ./.git/

RUN python3 -m venv /tmp/version-venv && \
    /tmp/version-venv/bin/pip install --no-cache-dir setuptools-scm && \
    /tmp/version-venv/bin/python -c "import setuptools_scm; print(setuptools_scm.get_version(root='/build', relative_to='/build/pyproject.toml', version_file='moviedb_manager/_version.py'))" > /tmp/app_version

WORKDIR /build/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN APP_VERSION="$(cat /tmp/app_version)" && \
    printf 'VITE_APP_VERSION=%s\n' "$APP_VERSION" > .env.production && \
    npm run build

# Stage 2: Build the Python application
FROM python:3.14-slim
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Create non-root user
RUN groupadd -r moviedb && useradd -r -g moviedb moviedb

WORKDIR /app

# Copy application code and git metadata
COPY moviedb_manager/ ./moviedb_manager/
COPY pyproject.toml .
COPY README.md .

# Reuse the git-derived version computed in the frontend stage
COPY --from=frontend-builder /tmp/app_version /tmp/app_version

# Copy built frontend assets
COPY --from=frontend-builder /build/frontend/dist ./moviedb_manager/static

# Install dependencies
RUN SETUPTOOLS_SCM_PRETEND_VERSION_FOR_MOVIEDB_MANAGER="$(cat /tmp/app_version)" \
    pip install --no-cache-dir .

# Create data directory
RUN mkdir -p /app/data && chown moviedb:moviedb /app/data

# Switch to non-root user
USER moviedb

# Expose port
EXPOSE 5000

# Health check (matches docker-compose)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/api/status')" || exit 1

# Command to run the application
CMD ["python", "-m", "moviedb_manager.app"]
