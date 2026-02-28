"""Pixabay API integration — free stock video and image search (fallback)."""

import httpx
from config.settings import settings

BASE_URL = "https://pixabay.com/api"


def search_videos(query: str, per_page: int = 5) -> list:
    """Search Pixabay for stock videos."""
    response = httpx.get(
        f"{BASE_URL}/videos/",
        params={"key": settings.PIXABAY_API_KEY, "q": query, "per_page": per_page},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()

    return [
        {
            "id": v["id"],
            "duration": v.get("duration"),
            "videos": v.get("videos", {}),
            "tags": v.get("tags"),
        }
        for v in data.get("hits", [])
    ]


def search_images(query: str, per_page: int = 5) -> list:
    """Search Pixabay for stock images."""
    response = httpx.get(
        f"{BASE_URL}/",
        params={"key": settings.PIXABAY_API_KEY, "q": query, "per_page": per_page, "image_type": "photo"},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()

    return [
        {
            "id": img["id"],
            "largeImageURL": img.get("largeImageURL"),
            "webformatURL": img.get("webformatURL"),
            "tags": img.get("tags"),
        }
        for img in data.get("hits", [])
    ]
