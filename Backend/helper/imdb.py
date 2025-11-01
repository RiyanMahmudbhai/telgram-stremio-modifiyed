import httpx
import re
from typing import Optional, Dict, Any

BASE_URL = "https://v3-cinemeta.strem.io"

def extract_first_year(year_string) -> int:
    if not year_string:
        return 0
    year_str = str(year_string)
    year_match = re.search(r'(\d{4})', year_str)
    if year_match:
        return int(year_match.group(1))
    return 0


async def search_title(query: str, type: str) -> Optional[Dict[str, Any]]:
    async with httpx.AsyncClient() as client:
        cinemeta_type = "series" if type == "tvSeries" else type  
        url = f"{BASE_URL}/catalog/{cinemeta_type}/imdb/search={query}.json"
        try:
            response = await client.get(url, timeout=10.0)
            if response.status_code != 200:
                return None
            data = response.json()
            
            if data and 'metas' in data and data['metas']:
                meta = data['metas'][0]
                return {
                    'id': meta.get('imdb_id', meta.get('id', '')),
                    'type': type,  
                    'title': meta.get('name', ''),
                    'year': meta.get('releaseInfo', ''),
                    'poster': meta.get('poster', '')
                }
            
            return None  
        except Exception:
            return None

async def get_detail(imdb_id: str) -> Optional[Dict[str, Any]]:
    async with httpx.AsyncClient() as client:
        for media_type in ['movie', 'series']:
            try:
                url = f"{BASE_URL}/meta/{media_type}/{imdb_id}.json"
                response = await client.get(url, timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    if 'meta' in data:
                        meta = data['meta']
                        year_value = 0
                        for year_field in ['year', 'releaseInfo', 'released']:
                            if meta.get(year_field):
                                year_value = extract_first_year(meta[year_field])
                                if year_value > 0:
                                    break
                        return {
                            'id': meta.get('imdb_id', meta.get('id', '')),
                            'type': meta.get('type', media_type),
                            'title': meta.get('name', ''),
                            'plot': meta.get('description', ''),
                            'genre': meta.get('genres', []) or meta.get('genre', []),
                            'releaseDetailed': {
                                'year': year_value
                            },
                            'rating': {
                                'star': float(meta.get('imdbRating', '0')) if meta.get('imdbRating') else 0
                            },
                            'poster': meta.get('poster', ''),
                            'background': meta.get('background', ''),
                            'logo': meta.get('logo', ''),
                            'runtime': meta.get('runtime', ''),
                            'director': meta.get('director', []),
                            'cast': meta.get('cast', []),
                            'videos': meta.get('videos', [])
                        }
                        
            except Exception:
                continue
        return None

async def get_season(imdb_id: str, season_id: int, episode_id: int) -> Optional[Dict[str, Any]]:
    async with httpx.AsyncClient() as client:
        try:
            url = f"{BASE_URL}/meta/series/{imdb_id}.json"
            response = await client.get(url, timeout=10.0)
            if response.status_code != 200:
                return None
            data = response.json()
            
            if 'meta' in data and 'videos' in data['meta']:
                for video in data['meta']['videos']:
                    if (str(video.get('season', '')) == str(season_id) and 
                        str(video.get('episode', '')) == str(episode_id)):
                        return {
                            'title': video.get('title', f'Episode {episode_id}'),
                            'no': str(episode_id),
                            'season': str(season_id),
                            'image': video.get('thumbnail', ''),
                            'plot': video.get('overview', ''),
                            'released': video.get('released', '')
                        }
            
            return None   
        except Exception:
            return None
