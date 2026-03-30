# AGENTS.md

This file provides guidance to AI coding assistants when working with code in this repository.

## Architecture

This is a movie and TV show download manager with a FastAPI backend and React frontend. The system features:

- **Backend**: FastAPI with SQLAlchemy 2.0 (async), PostgreSQL 15, Redis 7 (for live status), qBittorrent integration. Target Python version is 3.14.
- **Frontend**: React (Vite-based) with TypeScript.
- **Infrastructure**: Docker Compose for development and testing.
- **APIs**: Integration with TMDB and TVDB v4 for media metadata.

Core features include magnet link submission, automatic processing pipeline for torrents, live status updates via SSE, and a history of completed downloads with automatic file renaming/organization.

## Development Setup

### Environment Setup
Required environment variables (create `.env` file):
- `MOVIEDB_DATABASE_NAME`: Database name (default: `moviedb`)
- `MOVIEDB_DATABASE_USER`: Database user (default: `moviedb`)
- `MOVIEDB_DATABASE_PASSWORD`: Database password (default: `moviedb`)
- `MOVIEDB_DATABASE_HOST`: Database host (default: `db` in Docker, `localhost` locally)
- `MOVIEDB_DATABASE_PORT`: Database port (default: `5432`)
- `MOVIEDB_APIKEYS_TMDB`: API key for TMDB
- `MOVIEDB_APIKEYS_TVDB`: API key for TVDB v4
- `MOVIEDB_QBITTORRENT_HOST`: qBittorrent host (default: `qbittorrent` in Docker)
- `MOVIEDB_QBITTORRENT_PORT`: qBittorrent port (default: `8080`)
- `MOVIEDB_QBITTORRENT_USER`: qBittorrent username (default: `admin`)
- `MOVIEDB_QBITTORRENT_PASSWORD`: qBittorrent password (default: `adminadmin`)
- `MOVIEDB_REDIS_URL`: Redis connection URL (default: `redis://redis:6379/0` in Docker)

### Development Commands

**Primary development workflow:**
```bash
# Start development environment with live reload
./dev.sh start

# View logs
./dev.sh logs

# Stop development environment
./dev.sh stop

# Restart development environment
./dev.sh restart
```

**Testing:**
```bash
# Run tests in an isolated Docker environment
./dev.sh test
```

**Code Quality:**
```bash
# Pre-commit hooks should be installed
pre-commit install
pre-commit run --all-files
```

## Key File Locations

- `moviedb_manager/app.py`: FastAPI application entry point and route handlers.
- `moviedb_manager/api/`: API adapters for TMDB and TVDB.
- `moviedb_manager/db/`: Database session and model definitions.
- `moviedb_manager/models/`: Shared data models (e.g., media types).
- `moviedb_manager/services/`: Core business logic:
    - `torrent.py`: Torrent management and status tracking.
    - `metadata.py`: Fetching and processing media metadata.
    - `naming.py`: File renaming and organization logic.
    - `fileops.py`: Local file system operations.
    - `pipeline.py`: Orchestration of the download-to-organize workflow.
- `frontend/`: React frontend application.
- `alembic/`: Database migration files.
- `tests/`: Comprehensive test suite (api, services, pipeline).

## API Architecture

**Key endpoints:**
- `GET /api/status`: System health and version info.
- `POST /api/torrents`: Submit a new magnet link for processing.
- `GET /api/torrents`: List active and recent torrents.
- `GET /api/torrents/stream`: SSE endpoint for live torrent status updates.
- `GET /api/history`: Get history of completed downloads.

## Access URLs

**Development:**
- Application: http://localhost:6001
- Backend API Docs: http://localhost:6003/docs

## Code Conventions

- **Backend**: Python 3.11+, actively targeting 3.14 (see Dockerfile and pyproject.toml), type hints required, use `from __future__ import annotations`.
- **Frontend**: TypeScript strict mode.
- **Testing**: Functional tests preferred over class-based tests in Python. Use `pytest`.
- **Formatters**: Ruff for Python, Prettier/ESLint for JS/TS (via pre-commit).

## Common Development Issues

### Database Migrations
- Use Alembic for migrations.
- Apply migrations: `docker compose exec backend alembic upgrade head`

### API Authentication
- If you see `TMDB login failed` or `TVDB login failed` in logs, check your `.env` keys.
- qBittorrent connection errors usually mean the container isn't ready or credentials are wrong.

### Hot Reload in Docker
- The `dev.sh start` command mounts the source code into the containers to enable live reload.
- If changes aren't reflecting, try `./dev.sh restart`.
