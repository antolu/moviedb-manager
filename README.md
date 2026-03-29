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
| `MOVIEDB_APIKEYS_TMDB` | **Required** TMDB API Key | - |
| `MOVIEDB_APIKEYS_TVDB` | **Required** TVDB v4 API Key | - |
| `MOVIEDB_DATABASE_HOST` | Database host | `db` |
| `MOVIEDB_DATABASE_PORT` | Database port | `5432` |
| `MOVIEDB_DATABASE_USER` | Database user | `moviedb` |
| `MOVIEDB_DATABASE_PASSWORD` | Database password | `moviedb` |
| `MOVIEDB_DATABASE_NAME` | Database name | `moviedb` |
| `MOVIEDB_REDIS_URL` | Redis connection URL | `redis://redis:6379/0` |
| `MOVIEDB_QBITTORRENT_HOST`| qBittorrent host | `qbittorrent` |
| `MOVIEDB_QBITTORRENT_PORT`| qBittorrent WebUI port | `8080` |
| `MOVIEDB_QBITTORRENT_USER`| qBittorrent username | `admin` |
| `MOVIEDB_QBITTORRENT_PASSWORD`| qBittorrent password | `adminadmin` |
| `MOVIEDB_SECURITY_AUTH_BASE_URL` | `haochen.lu` base URL | `http://localhost` |
| `MOVIEDB_SECURITY_CLIENT_ID` | First-party auth client ID | - |
| `MOVIEDB_SECURITY_CLIENT_SECRET` | First-party auth client secret | - |
| `MOVIEDB_SECURITY_REDIRECT_URI` | OAuth callback URL for this app | `http://localhost:6001/auth/callback` |

Frontend build variables:

| Variable | Description | Default (Dev) |
| :--- | :--- | :--- |
| `VITE_AUTH_BASE_URL` | `haochen.lu` base URL | `http://localhost` |
| `VITE_AUTH_CLIENT_ID` | First-party auth client ID | - |
| `VITE_AUTH_REDIRECT_URI` | OAuth callback URL for this app | `http://localhost:6001/auth/callback` |

### Volume Mappings

Ensure the following volumes are mapped correctly to persist data and media:

| Host Path | Container Path | Purpose |
| :--- | :--- | :--- |
| `./downloads` | `/data/downloads` | Temporary download location for qBittorrent |
| `./data/movies` | `/data/movies` | Final library for organized movies |
| `./data/tv` | `/data/tv` | Final library for organized TV shows |

#### Connecting to an Existing Database
If you are using a managed database service (e.g., Supabase, RDS), set `MOVIEDB_DATABASE__HOST` to your platform's host and omit any local database volume mapping (like `./pgdata`) from your compose file.

## Auth

`moviedb-manager` is designed to authenticate through `haochen.lu`.

- The frontend redirects to the portfolio login if there is no valid session.
- `haochen.lu` returns the browser to `moviedb-manager` with an auth code.
- The `moviedb-manager` backend exchanges that code using its `client_secret`.
- The backend stores the returned access token in an HTTP-only cookie.
- Protected API routes validate that token by calling `haochen.lu /api/auth/me`.

For the sub-app registry in `haochen.lu`, register:

- `url`: the main app URL
- `admin_url`: optional admin landing URL
- `redirect_uris`: include `${MOVIEDB_SECURITY__REDIRECT_URI}`

### Local Docker wiring

The local dev compose joins the shared Docker network `first-party-auth-network`.

- The `haochen.lu` backend is reachable from the app container at
  `http://auth-broker:8000`
- The browser still uses `http://localhost/login`
- Set `MOVIEDB_SECURITY__AUTH_BASE_URL=http://auth-broker:8000`
- Set `VITE_AUTH_BASE_URL=http://localhost`

## 📜 License

This project is licensed under the **PolyForm Noncommercial License 1.0.0**. See the [LICENSE.md](LICENSE.md) file for details.
