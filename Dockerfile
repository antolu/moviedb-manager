FROM python:3.11-slim

# Set environment variables for production
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV FLASK_ENV=production

# Create non-root user for security
RUN groupadd -r moviedb && useradd -r -g moviedb moviedb

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy application code and git metadata for version detection (required by setuptools-scm)
COPY moviedb_manager/ ./moviedb_manager/
COPY pyproject.toml .
COPY README.md .
COPY .git/ ./.git/

# Install the application with all dependencies
RUN pip install .

# Create data directory for persistent config (if needed by app)
RUN mkdir -p /app/data && chown moviedb:moviedb /app/data

# Switch to non-root user
USER moviedb

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:5000/mediamanager || exit 1

# Environment variables for configuration (optional, defaults are provided in app)
# MOVIEDB_APIKEYS__TMDB: TMDB API Key
# MOVIEDB_APIKEYS__TVDB: TVDB API Key
# MOVIEDB_QBITTORRENT__HOST: qBittorrent host
# MOVIEDB_QBITTORRENT__PORT: qBittorrent port
# MOVIEDB_QBITTORRENT__USER: qBittorrent user
# MOVIEDB_QBITTORRENT__PASSWORD: qBittorrent password
# MOVIEDB_DIRECTORIES__REMOTE: Remote download directory
# MOVIEDB_DIRECTORIES__DOWNLOAD: Download subdirectory
# MOVIEDB_DIRECTORIES__LOCAL: Local data directory
# MOVIEDB_DIRECTORIES__MOVIE: Movie library subdirectory
# MOVIEDB_DIRECTORIES__TV: TV library subdirectory

# Set the command to run the application
CMD ["python", "-m", "moviedb_manager.app"]
