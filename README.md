# moviedb-manager

A modern movie and TV show download manager designed to automate your media library organization.

## Overview

`moviedb-manager` provides a streamlined interface to submit torrent links, track download status in real-time, and automatically organize completed media files with metadata from TMDB and TVDB.

## 🛠 Tech Stack

- **Backend**: FastAPI (Python 3.14) with SQLAlchemy 2.0
- **Frontend**: React (Vite) with TypeScript & Tailwind CSS
- **Database**: PostgreSQL 17
- **Caching/Status**: Redis 7
- **Downloader**: qBittorrent integration
- **Metadata**: TMDB & TVDB v4 integration

## 🐳 Docker Deployment

The application is designed to be run using Docker Compose.

### Required External Services

- **PostgreSQL**: For persistent storage.
- **Redis**: For live status updates via SSE.
- **qBittorrent**: For handling torrent downloads.

### Environment Variables

Configure the following variables in a `.env` file or directly in your environment:

| Variable | Description | Default (Dev) |
| :--- | :--- | :--- |
| `MOVIEDB_APIKEYS__TMDB` | **Required** TMDB API Key | - |
| `MOVIEDB_APIKEYS__TVDB` | **Required** TVDB v4 API Key | - |
| `MOVIEDB_DATABASE__HOST` | Database host | `db` |
| `MOVIEDB_DATABASE__PORT` | Database port | `5432` |
| `MOVIEDB_DATABASE__USER` | Database user | `moviedb` |
| `MOVIEDB_DATABASE__PASSWORD` | Database password | `moviedb` |
| `MOVIEDB_DATABASE__NAME` | Database name | `moviedb` |
| `MOVIEDB_REDIS__URL` | Redis connection URL | `redis://redis:6379/0` |
| `MOVIEDB_QBITTORRENT__HOST`| qBittorrent host | `qbittorrent` |
| `MOVIEDB_QBITTORRENT__PORT`| qBittorrent WebUI port | `8080` |
| `MOVIEDB_QBITTORRENT__USER`| qBittorrent username | `admin` |
| `MOVIEDB_QBITTORRENT__PASSWORD`| qBittorrent password | `adminadmin` |

### Volume Mappings

Ensure the following volumes are mapped correctly to persist data and media:

| Host Path | Container Path | Purpose |
| :--- | :--- | :--- |
| `./downloads` | `/data/downloads` | Temporary download location for qBittorrent |
| `./data/movies` | `/data/movies` | Final library for organized movies |
| `./data/tv` | `/data/tv` | Final library for organized TV shows |

#### Connecting to an Existing Database
If you are using a managed database service (e.g., Supabase, RDS), set `MOVIEDB_DATABASE__HOST` to your platform's host and omit any local database volume mapping (like `./pgdata`) from your compose file.

## 📜 License

This project is licensed under the **PolyForm Noncommercial License 1.0.0**. See the [LICENSE.md](LICENSE.md) file for details.
