import asyncio
import traceback
import PTN
from re import compile, IGNORECASE
from Backend.helper.imdb import get_detail, get_season, search_title
from Backend.helper.pyro import extract_tmdb_id
from themoviedb import aioTMDb
from Backend.config import Telegram
import Backend
from Backend.logger import LOGGER
from Backend.helper.encrypt import encode_string

# ----------------- Configuration -----------------
DELAY = 2
tmdb = aioTMDb(key=Telegram.TMDB_API, language="en-US", region="US")

# ----------------- Helpers -----------------
def format_tmdb_image(path: str, size="w500") -> str:
    return f"https://image.tmdb.org/t/p/{size}{path}"

def format_imdb_images(imdb_id: str) -> dict:
    return {
        "poster": f"https://images.metahub.space/poster/small/{imdb_id}/img",
        "backdrop": f"https://images.metahub.space/background/medium/{imdb_id}/img",
        "logo": f"https://images.metahub.space/logo/medium/{imdb_id}/img",
    }

async def safe_imdb_search(title: str, type_: str) -> str | None:
    """Safely search IMDb title and return its ID."""
    try:
        result = await search_title(query=title, type=type_)
        return result["id"] if result else None
    except Exception as e:
        LOGGER.warning(f"IMDb search failed for '{title}' [{type_}]: {e}")
        return None

async def safe_tmdb_search(title: str, type_: str, year=None):
    """Safely search TMDb title."""
    try:
        if type_ == "movie":
            if year:
                results = await tmdb.search().movies(query=title, year=year)
            else:
                results = await tmdb.search().movies(query=title)
        else:
            results = await tmdb.search().tv(query=title)
        return results[0] if results else None
    except Exception as e:
        LOGGER.error(f"TMDb search failed for '{title}' [{type_}]: {e}")
        return None

# ----------------- Main Entry -----------------
async def metadata(filename: str, channel: int, msg_id) -> dict | None:
    try:
        parsed = PTN.parse(filename)
    except Exception as e:
        LOGGER.error(f"PTN parsing failed for {filename}: {e}\n{traceback.format_exc()}")
        return None
    
    # Skip combined/invalid files
    if "excess" in parsed and any("combined" in item.lower() for item in parsed["excess"]):
        LOGGER.info(f"Skipping {filename}: contains 'combined'")
        return None
    
    # Skip split/multipart files
    multipart_pattern = compile(r'(?:part|cd|disc|disk)[s._-]*\d+(?=\.\w+$)', IGNORECASE)
    if multipart_pattern.search(filename):
        LOGGER.info(f"Skipping {filename}: seems to be a split/multipart file")
        return None
    
    title = parsed.get("title")
    season = parsed.get("season")
    episode = parsed.get("episode")
    year = parsed.get("year")
    quality = parsed.get("resolution")
    
    if not quality:
        LOGGER.warning(f"Skipping {filename}: No resolution (parsed={parsed})")
        return None
    
    if isinstance(season, list) or isinstance(episode, list):
        LOGGER.warning(f"Invalid season/episode format for {filename}: {parsed}")
        return None
    
    if season and not episode:
        LOGGER.warning(f"Missing episode in {filename}: {parsed}")
        return None
    
    # Extract TMDb/IMDb hint
    default_id = None
    try:
        default_id = extract_tmdb_id(Backend.USE_DEFAULT_ID)
    except Exception:
        pass
    
    if not default_id:
        try:
            default_id = extract_tmdb_id(filename)
        except Exception:
            pass
    
    if not title:
        LOGGER.info(f"No title parsed from: {filename} (parsed={parsed})")
        return None
    
    data = {"chat_id": channel, "msg_id": msg_id}
    encoded_string = await encode_string(data)
    
    try:
        if season and episode:
            LOGGER.info(f"Fetching TV metadata: {title} S{season}E{episode}")
            return await fetch_tv_metadata(title, season, episode, encoded_string, year, quality, default_id)
        else:
            LOGGER.info(f"Fetching Movie metadata: {title} ({year})")
            return await fetch_movie_metadata(title, encoded_string, year, quality, default_id)
    except Exception as e:
        LOGGER.error(f"Error while fetching metadata for {filename}: {e}\n{traceback.format_exc()}")
        return None

# ----------------- TV Metadata -----------------
async def fetch_tv_metadata(title, season, episode, encoded_string, year=None, quality=None, default_id=None) -> dict | None:
    imdb_id = default_id if default_id and default_id.startswith("tt") else await safe_imdb_search(title, "tvSeries")
    tv_details, ep_details, use_tmdb = None, None, False
    
    # Try IMDb first
    if imdb_id:
        try:
            await asyncio.sleep(DELAY)
            tv_details = await get_detail(imdb_id=imdb_id)
            await asyncio.sleep(DELAY)
            ep_details = await get_season(imdb_id=imdb_id, season_id=season, episode_id=episode)
        except Exception as e:
            LOGGER.warning(f"IMDb TV fetch failed [{imdb_id}]: {e}")
    
    # IMDb failed → fallback to TMDb
    if not tv_details and not ep_details:
        use_tmdb = True
        tmdb_result = await safe_tmdb_search(title, "tv")
        if not tmdb_result:
            LOGGER.warning(f"No TMDb result for '{title}'")
            return None
        
        tv_id = tmdb_result.id
        try:
            tv_details = await tmdb.tv(tv_id).details(append_to_response="external_ids")
        except Exception as e:
            LOGGER.warning(f"TMDb TV details failed for {title}: {e}")
            return None
        
        # Fetch episode safely
        try:
            ep_details = await tmdb.episode(tv_id, season, episode).details()
        except Exception as e:
            LOGGER.warning(f"TMDb episode not found for {title} S{season}E{episode}: {e}")
            ep_details = None
    
    # Return TMDb-based data
    if use_tmdb and tv_details:
        return {
            "tmdb_id": tv_details.id,
            "imdb_id": tv_details.external_ids.imdb_id,
            "title": tv_details.name,
            "year": getattr(tv_details.first_air_date, "year", 0),
            "rate": getattr(tv_details, "vote_average", 0) or 0,
            "description": tv_details.overview or "",
            "poster": format_tmdb_image(tv_details.poster_path),
            "backdrop": format_tmdb_image(tv_details.backdrop_path, "original"),
            "logo": "",
            "genres": [g.name for g in (tv_details.genres or [])],
            "media_type": "tv",
            "season_number": season,
            "episode_number": episode,
            "episode_title": getattr(ep_details, "name", f"S{season}E{episode}") if ep_details else f"{tv_details.name} S{season}E{episode}",
            "episode_backdrop": format_tmdb_image(getattr(ep_details, "still_path", None), "original") if ep_details else "",
            "quality": quality,
            "encoded_string": encoded_string,
        }
    
    # IMDb-based data
    if not tv_details:
        LOGGER.warning(f"No valid IMDb data for {title}")
        return None
    
    imdb_id = tv_details.get("id", "")
    images = format_imdb_images(imdb_id)
    
    return {
        "tmdb_id": imdb_id.replace("tt", ""),
        "imdb_id": imdb_id,
        "title": tv_details.get("title", title),
        "year": tv_details.get("releaseDetailed", {}).get("year", 0),
        "rate": tv_details.get("rating", {}).get("star", 0),
        "description": tv_details.get("plot", ""),
        "poster": images["poster"],
        "backdrop": images["backdrop"],
        "logo": images["logo"],
        "genres": tv_details.get("genre", []),
        "media_type": "tv",
        "season_number": season,
        "episode_number": episode,
        "episode_title": ep_details.get("title", f"S{season}E{episode}") if ep_details else f"{tv_details.get('title', title)} S{season}E{episode}",
        "episode_backdrop": ep_details.get("image", "") if ep_details else "",
        "quality": quality,
        "encoded_string": encoded_string,
    }

# ----------------- Movie Metadata -----------------
async def fetch_movie_metadata(title, encoded_string, year=None, quality=None, default_id=None) -> dict | None:
    imdb_id = default_id if default_id and default_id.startswith("tt") else await safe_imdb_search(f"{title} {year}" if year else title, "movie")
    movie_details, use_tmdb = None, False
    
    # Try IMDb first
    if imdb_id:
        try:
            movie_details = await get_detail(imdb_id=imdb_id)
        except Exception as e:
            LOGGER.warning(f"IMDb movie fetch failed [{title}]: {e}")
    
    # IMDb failed → fallback to TMDb
    if not movie_details:
        use_tmdb = True
        tmdb_result = await safe_tmdb_search(title, "movie", year)
        if not tmdb_result:
            LOGGER.warning(f"No TMDb movie found for '{title}'")
            return None
        
        try:
            movie_details = await tmdb.movie(tmdb_result.id).details(append_to_response="external_ids")
        except Exception as e:
            LOGGER.warning(f"TMDb movie details failed for {title}: {e}")
            return None
    
    # TMDb result
    if use_tmdb and movie_details:
        return {
            "tmdb_id": movie_details.id,
            "imdb_id": movie_details.external_ids.imdb_id,
            "title": movie_details.title,
            "year": getattr(movie_details.release_date, "year", 0),
            "rate": getattr(movie_details, "vote_average", 0) or 0,
            "description": movie_details.overview or "",
            "poster": format_tmdb_image(movie_details.poster_path),
            "backdrop": format_tmdb_image(movie_details.backdrop_path, "original"),
            "logo": "",
            "media_type": "movie",
            "genres": [g.name for g in (movie_details.genres or [])],
            "quality": quality,
            "encoded_string": encoded_string,
        }
    
    # IMDb result
    imdb_id = movie_details.get("id", "")
    images = format_imdb_images(imdb_id)
    
    return {
        "tmdb_id": imdb_id.replace("tt", ""),
        "imdb_id": imdb_id,
        "title": movie_details.get("title", title),
        "year": movie_details.get("releaseDetailed", {}).get("year", 0),
        "rate": movie_details.get("rating", {}).get("star", 0),
        "description": movie_details.get("plot", ""),
        "poster": images["poster"],
        "backdrop": images["backdrop"],
        "logo": images["logo"],
        "media_type": "movie",
        "genres": movie_details.get("genre", []),
        "quality": quality,
        "encoded_string": encoded_string,
    }
