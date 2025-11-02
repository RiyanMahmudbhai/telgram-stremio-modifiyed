# Telegram Stremio Media Server - AI Agent Instructions

## Project Overview

This is a self-hosted Telegram-to-Stremio bridge that streams media from Telegram channels through Stremio. The system automatically extracts metadata from filenames, stores it in MongoDB, and exposes Stremio-compatible streaming APIs.

**Core Tech Stack**: FastAPI, PyroFork (Telegram client), MongoDB (Motor), TMDB/IMDb APIs, Docker

## Architecture & Data Flow

### Three-Component System

1. **Telegram Bot Layer** (`Backend/pyrofork/`): Receives files forwarded to `AUTH_CHANNEL`, extracts metadata using PTN (Parse Torrent Name)
2. **Database Layer** (`Backend/helper/database.py`): Multi-MongoDB system with 1 tracking DB + N storage DBs for load distribution
3. **FastAPI Web Layer** (`Backend/fastapi/`): Serves Stremio addon APIs and admin dashboard

### Critical Flow

```
Telegram File → reciever.py → metadata.py (PTN parse + TMDB/IMDb fetch) → database.py (insert/update) → stremio_routes.py (catalog/stream APIs)
```

Files forwarded to `AUTH_CHANNEL` trigger `reciever.py`, which queues them for async processing. Metadata extraction happens via `PTN.parse()` for filename patterns like `Movie.Name.2023.1080p.WEB-DL.mkv` or `Show.S01E05.720p.mkv`.

## Key Patterns & Conventions

### Multi-Database Architecture

- **First DB** (`tracking`): Stores state like current active storage DB index
- **Remaining DBs** (`storage_1`, `storage_2`, ...): Store actual media documents, round-robin on full DB
- All database methods in `database.py` check `current_db_index` and auto-switch on storage errors
- Documents include `db_index` field to track which storage DB holds them

### Quality Replacement Logic

When uploading the same movie/episode with the same quality (e.g., `720p`), the system **replaces** the old entry instead of creating duplicates. This is handled in `database.py`'s `update_movie()` and `update_tv()` methods by finding existing quality entries and overwriting.

### Pydantic Schemas (`Backend/helper/modal.py`)

- `MovieSchema`: Flat structure with `telegram: List[QualityDetail]` for different qualities
- `TVShowSchema`: Nested `seasons → episodes → telegram` structure
- Always validate with Pydantic before DB insertion to catch schema errors early

### Multi-Token Load Balancing

`MULTI_TOKEN1`, `MULTI_TOKEN2`, etc. environment variables create multiple Telegram clients to distribute API rate limits. `work_loads` dict in `bot.py` tracks usage per client. Streaming picks the least-loaded client via `min(work_loads, key=work_loads.get)`.

### Filename Parsing Requirements

- **Movies**: Must include title, year, and quality (e.g., `Inception.2010.1080p.BluRay.mkv`)
- **TV Shows**: Must include title, season (`S01`), episode (`E05`), and quality
- Files without quality labels are **skipped** (see `metadata.py:74`)
- Multipart files (`Part1`, `CD1`) and "combined" files are automatically rejected

### Manual Upload with `/set` Command

Users can override automatic parsing by sending `/set <imdb_url>`, which sets `Backend.USE_DEFAULT_ID`. Subsequent file uploads use this ID instead of searching. Cleared by sending `/set` without arguments.

### Scanning Existing Videos with `/scan` Command

The bot only processes **new messages in real-time** by default via `reciever.py`. To detect videos that were already uploaded to `AUTH_CHANNEL` before the bot started:

**Command Formats:**

- `/scan` - Scans messages 1-100 (default)
- `/scan [limit]` - Scans messages 1 to limit
- `/scan <start> <end>` - Scans messages from start to end (batch scanning)

**Examples:**

- `/scan 500` - Scans messages 1-500
- `/scan 100 500` - Scans messages 100-500 (useful for large channels)
- `/scan 1 3500` - Scans all messages 1-3500 (for channels with 3000+ videos)

**Features:**

- Maximum 10,000 messages per scan (prevents timeouts)
- Checks if files already exist in DB before adding (avoids duplicates)
- Uses same metadata extraction pipeline as real-time processing
- Shows progress updates every 10 files
- Implemented in `Backend/pyrofork/plugins/scan.py`

## Development Workflows

### Local Development Setup

```bash
# Install dependencies (requires UV package manager)
uv sync

# Configure environment
cp sample_config.env config.env
# Edit config.env with required values (see README.md Configuration Guide)

# Run locally
uv run -m Backend
```

### Docker Deployment

```bash
# Build and run
docker compose up -d

# Update config without rebuild (volume-mounted)
nano config.env
docker compose restart

# View logs
docker compose logs -f
```

### Testing Metadata Extraction

Use `mcp_pylance_mcp_s_pylanceRunCodeSnippet` to test PTN parsing:

```python
import PTN
parsed = PTN.parse("Ghosted.2023.720p.WEBRip.x265.mkv")
print(parsed)  # {'title': 'Ghosted', 'year': 2023, 'resolution': '720p', ...}
```

### Debugging Database Issues

- Check `log.txt` for validation errors (Pydantic failures appear as "Update failed due to validation errors")
- Verify `current_db_index` in tracking DB: `db.dbs["tracking"]["state"].find_one({"_id": "db_index"})`
- Inspect documents: Movies in `movies` collection, TV shows in `tv_shows`, both include `db_index` field

## File Organization

- `Backend/config.py`: Loads all env vars from `config.env`, no defaults for sensitive values
- `Backend/fastapi/routes/`: All HTTP endpoints split by concern (stream, stremio, templates, API)
- `Backend/helper/`: Utility modules for database, encryption, metadata, Telegram helpers
- `Backend/pyrofork/plugins/`: Telegram bot command handlers (auto-loaded by PyroFork)

## Bot Commands

| Command               | Description                                                                 | Access     |
| --------------------- | --------------------------------------------------------------------------- | ---------- |
| `/start`              | Returns Stremio addon URL for installation                                  | Owner only |
| `/log`                | Sends latest log file for debugging                                         | Owner only |
| `/set <imdb_url>`     | Manual upload by linking IMDb URL, then forward files                       | Owner only |
| `/set`                | Clear default IMDb link                                                     | Owner only |
| `/restart`            | Restart bot and pull updates from upstream repo                             | Owner only |
| `/scan [limit]`       | Scan messages 1 to limit (default: 100)                                     | Owner only |
| `/scan <start> <end>` | Batch scan messages from start to end (e.g., `/scan 100 500` scans 100-500) | Owner only |

## Important Gotchas

1. **At least 2 MongoDB URIs required**: System enforces `len(DATABASE) >= 2` in `database.py:31`
2. **Quality replacement**: Same quality → replaces old file (prevents duplicates in Stremio)
3. **Encoded streaming URLs**: All streaming URLs use encrypted `{chat_id, msg_id}` via `encode_string()` in `encrypt.py`
4. **Session persistence**: `StreamBot` and `Helper` clients create `.session` files; don't commit these
5. **Auto-updates on restart**: `/restart` command pulls latest from `UPSTREAM_REPO` via `update.py` git commands
6. **Admin auth**: Uses simple session-based auth in `security/credentials.py`, credentials in `config.env`
7. **Real-time only by default**: Bot only processes new forwarded messages; use `/scan` to detect pre-existing videos

## External Dependencies

- **TMDB_API**: Required for metadata fallback when IMDb fails
- **AUTH_CHANNEL**: Comma-separated Telegram channel IDs (format: `-1001234567890`)
- **BASE_URL**: Public domain for Stremio addon installation (e.g., `https://yourdomain.com`)

## Testing Stremio Integration

1. Start server locally or deploy
2. Visit `http://localhost:8000/stremio` for setup guide
3. Install addon via `{BASE_URL}/stremio/manifest.json` in Stremio
4. Forward a movie file to `AUTH_CHANNEL` with proper naming
5. Check catalog at `/stremio/catalog/movie/latest_movies.json`

## Common Modifications

### Adding New Catalog Filters

Edit `stremio_routes.py` manifest catalogs, then implement filter logic in catalog handlers (check `genre` query param pattern).

### Adjusting Metadata Extraction

Modify `metadata.py` PTN parsing logic. Key functions: `fetch_movie_metadata()` and `fetch_tv_metadata()`.

### Changing Quality Replacement Behavior

Edit `database.py` methods `update_movie()` or `update_tv()` where existing qualities are found and updated.
