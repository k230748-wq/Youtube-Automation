"""YouTube Data API integration — trending videos, search, keyword research."""

import httpx
from config.settings import settings

BASE_URL = "https://www.googleapis.com/youtube/v3"


def search_videos(query: str, max_results: int = 10, order: str = "relevance") -> list:
    """Search YouTube for videos matching a query."""
    response = httpx.get(
        f"{BASE_URL}/search",
        params={
            "key": settings.YOUTUBE_API_KEY,
            "q": query,
            "part": "snippet",
            "type": "video",
            "maxResults": max_results,
            "order": order,
        },
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()

    return [
        {
            "video_id": item["id"]["videoId"],
            "title": item["snippet"]["title"],
            "description": item["snippet"]["description"],
            "channel_title": item["snippet"]["channelTitle"],
            "published_at": item["snippet"]["publishedAt"],
            "thumbnail": item["snippet"]["thumbnails"].get("high", {}).get("url"),
        }
        for item in data.get("items", [])
    ]


def get_trending(region_code: str = "US", category_id: str = None, max_results: int = 10) -> list:
    """Get trending videos for a region."""
    params = {
        "key": settings.YOUTUBE_API_KEY,
        "part": "snippet,statistics",
        "chart": "mostPopular",
        "regionCode": region_code,
        "maxResults": max_results,
    }
    if category_id:
        params["videoCategoryId"] = category_id

    response = httpx.get(f"{BASE_URL}/videos", params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    return [
        {
            "video_id": item["id"],
            "title": item["snippet"]["title"],
            "channel_title": item["snippet"]["channelTitle"],
            "view_count": item["statistics"].get("viewCount"),
            "like_count": item["statistics"].get("likeCount"),
            "comment_count": item["statistics"].get("commentCount"),
            "tags": item["snippet"].get("tags", []),
        }
        for item in data.get("items", [])
    ]


def get_video_details(video_id: str) -> dict:
    """Get detailed info about a specific video."""
    response = httpx.get(
        f"{BASE_URL}/videos",
        params={
            "key": settings.YOUTUBE_API_KEY,
            "id": video_id,
            "part": "snippet,statistics,contentDetails",
        },
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    items = data.get("items", [])
    return items[0] if items else {}
