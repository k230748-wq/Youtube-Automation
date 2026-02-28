"""Pexels API integration — free stock video and image search."""

import httpx
from config.settings import settings

BASE_URL = "https://api.pexels.com"


def search_videos(query: str, orientation: str = "landscape", per_page: int = 5) -> list:
    """Search Pexels for stock videos."""
    response = httpx.get(
        f"{BASE_URL}/videos/search",
        headers={"Authorization": settings.PEXELS_API_KEY},
        params={"query": query, "orientation": orientation, "per_page": per_page},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()

    return [
        {
            "id": v["id"],
            "url": v["url"],
            "duration": v.get("duration"),
            "video_files": [
                {"link": f["link"], "quality": f.get("quality"), "width": f.get("width"), "height": f.get("height")}
                for f in v.get("video_files", [])
                if f.get("quality") in ("hd", "sd")
            ],
            "video_pictures": [p["picture"] for p in v.get("video_pictures", [])[:2]],
        }
        for v in data.get("videos", [])
    ]


def search_photos(query: str, orientation: str = "landscape", per_page: int = 5) -> list:
    """Search Pexels for stock photos."""
    response = httpx.get(
        f"{BASE_URL}/v1/search",
        headers={"Authorization": settings.PEXELS_API_KEY},
        params={"query": query, "orientation": orientation, "per_page": per_page},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()

    return [
        {
            "id": p["id"],
            "url": p["url"],
            "src": p.get("src", {}),
            "photographer": p.get("photographer"),
        }
        for p in data.get("photos", [])
    ]
