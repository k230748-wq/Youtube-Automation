"""SerpAPI integration — Google Trends, autocomplete, People Also Ask."""

import httpx
from config.settings import settings

BASE_URL = "https://serpapi.com/search"


def _search(params: dict) -> dict:
    """Make a SerpAPI request."""
    params["api_key"] = settings.SERPAPI_API_KEY
    response = httpx.get(BASE_URL, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def get_google_trends(query: str, geo: str = "US", timeframe: str = "today 12-m") -> dict:
    """Get Google Trends data for a query."""
    return _search({
        "engine": "google_trends",
        "q": query,
        "geo": geo,
        "date": timeframe,
    })


def get_related_searches(query: str, geo: str = "US") -> dict:
    """Get related searches from Google."""
    result = _search({
        "engine": "google",
        "q": query,
        "gl": geo.lower(),
    })
    return {
        "related_searches": result.get("related_searches", []),
        "related_questions": result.get("related_questions", []),
    }


def get_people_also_ask(query: str, gl: str = "us") -> list:
    """Get People Also Ask questions from Google."""
    result = _search({
        "engine": "google",
        "q": query,
        "gl": gl,
    })
    return result.get("related_questions", [])


def get_autocomplete(query: str, gl: str = "us") -> list:
    """Get Google autocomplete suggestions."""
    result = _search({
        "engine": "google_autocomplete",
        "q": query,
        "gl": gl,
    })
    return result.get("suggestions", [])


def get_keyword_data(query: str, gl: str = "us") -> dict:
    """Get keyword search results with organic data."""
    result = _search({
        "engine": "google",
        "q": query,
        "gl": gl,
        "num": 20,
    })
    return {
        "organic_results": result.get("organic_results", [])[:10],
        "search_information": result.get("search_information", {}),
        "related_searches": result.get("related_searches", []),
    }
