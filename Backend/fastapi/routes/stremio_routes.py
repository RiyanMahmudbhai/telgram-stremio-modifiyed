from fastapi import APIRouter, HTTPException
from typing import Optional
from urllib.parse import unquote
from Backend.config import Telegram
from Backend import db, __version__

# --- Configuration ---
BASE_URL = Telegram.BASE_URL
ADDON_NAME = "Telegram"
ADDON_VERSION = __version__
PAGE_SIZE = 15

router = APIRouter(prefix="/stremio", tags=["Stremio Addon"])

# Define available genres
GENRES = [
    "Action", "Adventure", "Animation", "Biography", "Comedy", 
    "Crime", "Documentary", "Drama", "Family", "Fantasy", 
    "History", "Horror", "Music", "Mystery", "Romance", 
    "Sci-Fi", "Sport", "Thriller", "War", "Western"
]

# --- Helper Functions ---
def convert_to_stremio_meta(item: dict) -> dict:
    media_type = "series" if item.get("media_type") == "tv" else "movie"
    stremio_id = f"{item.get('tmdb_id')}-{item.get('db_index')}"
    
    return {
        "id": stremio_id,
        "type": media_type,
        "name": item.get("title"),
        "poster": item.get("poster") or "",
        "logo": item.get("logo") or "",
        "year": item.get("release_year"),
        "background": item.get("backdrop") or "",
        "genres": item.get("genres") or [],
        "imdbRating": item.get("rating") or "",
        "description": item.get("description") or "",
    }

# --- Stremio Endpoints ---
@router.get("/manifest.json")
async def get_manifest():
    return {
        "id": "telegram.media",
        "version": ADDON_VERSION,
        "name": ADDON_NAME,
        "logo": "https://i.postimg.cc/XqWnmDXr/Picsart-25-10-09-08-09-45-867.png",
        "description": "Streams movies and series from your Telegram.",
        "types": ["movie", "series"],
        "resources": ["catalog", "meta", "stream"],
        "catalogs": [
            # Movie Catalogs
            {
                "type": "movie",
                "id": "latest_movies",
                "name": "Latest",
                "extra": [
                    {
                        "name": "genre",
                        "isRequired": False,
                        "options": GENRES
                    },
                    {"name": "skip"}
                ],
                "extraSupported": ["genre", "skip"]
            },
            {
                "type": "movie",
                "id": "top_movies",
                "name": "Popular",
                "extra": [
                    {
                        "name": "genre",
                        "isRequired": False,
                        "options": GENRES
                    },
                    {"name": "skip"},
                    {"name": "search", "isRequired": False}
                ],
                "extraSupported": ["genre", "skip", "search"]
            },
            # Series Catalogs
            {
                "type": "series",
                "id": "latest_series",
                "name": "Latest",
                "extra": [
                    {
                        "name": "genre",
                        "isRequired": False,
                        "options": GENRES
                    },
                    {"name": "skip"}
                ],
                "extraSupported": ["genre", "skip"]
            },
            {
                "type": "series",
                "id": "top_series",
                "name": "Popular",
                "extra": [
                    {
                        "name": "genre",
                        "isRequired": False,
                        "options": GENRES
                    },
                    {"name": "skip"},
                    {"name": "search", "isRequired": False}
                ],
                "extraSupported": ["genre", "skip", "search"]
            }
        ],
        "idPrefixes": [""],
        "behaviorHints": {
            "configurable": False,
            "configurationRequired": False
        }
            }
    
@router.get("/catalog/{media_type}/{id}/{extra:path}.json")
@router.get("/catalog/{media_type}/{id}.json")
async def get_catalog(media_type: str, id: str, extra: Optional[str] = None):
    if media_type not in ["movie", "series"]:
        raise HTTPException(status_code=404, detail="Invalid catalog type")
    
    genre_filter = None
    search_query = None
    stremio_skip = 0
    
    if extra:
        params = extra.replace("&", "/").split("/")
        for param in params:
            if param.startswith("genre="):
                genre_filter = unquote(param.removeprefix("genre="))
            elif param.startswith("search="):
                search_query = unquote(param.removeprefix("search="))
            elif param.startswith("skip="):
                try:
                    stremio_skip = int(param.removeprefix("skip="))
                except ValueError:
                    stremio_skip = 0
    
    page = (stremio_skip // PAGE_SIZE) + 1
    
    try:
        if search_query:
            search_results = await db.search_documents(query=search_query, page=page, page_size=PAGE_SIZE)
            all_items = search_results.get("results", [])
            db_media_type = "tv" if media_type == "series" else "movie"
            items = [item for item in all_items if item.get("media_type") == db_media_type]
        else:
            if "latest" in id:
                sort_params = [("updated_on", "desc")]
            elif "top" in id:
                sort_params = [("rating", "desc")]
            else:
                sort_params = [("updated_on", "desc")]
            
            if media_type == "movie":
                data = await db.sort_movies(sort_params, page, PAGE_SIZE, genre_filter=genre_filter)
                items = data.get("movies", [])
            else:
                data = await db.sort_tv_shows(sort_params, page, PAGE_SIZE, genre_filter=genre_filter)
                items = data.get("tv_shows", [])

    except Exception as e:
        print(f"Error fetching catalog data: {e}")
        return {"metas": []}
    
    metas = [convert_to_stremio_meta(item) for item in items]
    return {"metas": metas}

@router.get("/meta/{media_type}/{id}.json")
async def get_meta(media_type: str, id: str):
    try:
        tmdb_id_str, db_index_str = id.split("-")
        tmdb_id, db_index = int(tmdb_id_str), int(db_index_str)
    except (ValueError, IndexError):
        raise HTTPException(status_code=400, detail="Invalid Stremio ID format")
    
    media = await db.get_media_details(tmdb_id=tmdb_id, db_index=db_index)
    
    if not media:
        return {"meta": {}}
    
    meta_obj = {
        "id": id,
        "type": "series" if media.get("media_type") == "tv" else "movie",
        "name": media.get("title", ""),
        "description": media.get("description", ""),
        "year": str(media.get("release_year", "")),
        "imdbRating": str(media.get("rating", "")),
        "genres": media.get("genres", []),
        "poster": media.get("poster", ""),
        "logo": media.get("logo", ""),
        "background": media.get("backdrop", ""),
        "imdb_id": media.get("imdb_id", "")
    }
    
    if media_type == "series" and "seasons" in media:
        series_base_id = id
        videos = []
        
        for season in sorted(media.get("seasons", []), key=lambda s: s.get("season_number")):
            for episode in sorted(season.get("episodes", []), key=lambda e: e.get("episode_number")):
                episode_id = f"{series_base_id}:{season['season_number']}:{episode['episode_number']}"
                videos.append({
                    "id": episode_id,
                    "title": episode.get("title", f"Episode {episode['episode_number']}"),
                    "season": season.get("season_number"),
                    "episode": episode.get("episode_number"),
                    "thumbnail": episode.get("episode_backdrop") or "https://via.placeholder.com/1280x720/1a1a2e/eaeaea?text=No+Image",
                    "imdb_id": episode.get("imdb_id") or media.get("imdb_id"),
                })
        
        meta_obj["videos"] = videos
    
    return {"meta": meta_obj}

@router.get("/stream/{media_type}/{id}.json")
async def get_streams(media_type: str, id: str):
    try:
        parts = id.split(":")
        base_id = parts[0]
        season_num = int(parts[1]) if len(parts) > 1 else None
        episode_num = int(parts[2]) if len(parts) > 2 else None
        tmdb_id, db_index = map(int, base_id.split("-"))
    except (ValueError, IndexError):
        raise HTTPException(status_code=400, detail="Invalid Stremio ID format")
    
    media_details = await db.get_media_details(
        tmdb_id=tmdb_id,
        db_index=db_index,
        season_number=season_num,
        episode_number=episode_num
    )
    
    if not media_details or "telegram" not in media_details:
        return {"streams": []}
    
    streams = [
        {
            "name": f"{quality.get('name', '')}",
            "title": f"{quality.get('quality', 'HD')}\n💾 {quality.get('size', '')}",
            "url": f"{BASE_URL}/dl/{quality.get('id')}/video.mkv"
        }
        for quality in media_details.get("telegram", [])
        if quality.get("id")
    ]
    
    return {"streams": streams}
