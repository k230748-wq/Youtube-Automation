"""YouTube Upload integration — upload videos via YouTube Data API v3.

Requires OAuth2 credentials (not just an API key).
The API key is only for read operations; uploads need OAuth.

Setup:
1. Create OAuth2 credentials in Google Cloud Console
2. Download client_secrets.json and place in project root
3. Run authorize() once to generate token
"""

import os
import json
import structlog
import httpx

logger = structlog.get_logger(__name__)

TOKEN_FILE = "youtube_oauth_token.json"
CLIENT_SECRETS_FILE = "client_secrets.json"


def upload_video(
    video_path: str,
    title: str,
    description: str,
    tags: list = None,
    category_id: str = "22",  # People & Blogs
    privacy_status: str = "private",
    thumbnail_path: str = None,
) -> dict:
    """Upload a video to YouTube.

    Args:
        video_path: Path to the video file
        title: Video title (max 100 chars)
        description: Video description (max 5000 chars)
        tags: List of tags
        category_id: YouTube category ID (22 = People & Blogs)
        privacy_status: 'private', 'unlisted', or 'public'
        thumbnail_path: Optional path to custom thumbnail

    Returns:
        Dict with video_id and url on success.
    """
    token = _load_token()
    if not token:
        raise RuntimeError(
            "No YouTube OAuth token found. Run 'python -m app.integrations.youtube_upload_client' "
            "to authorize first."
        )

    access_token = token["access_token"]

    # Step 1: Upload the video
    metadata = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags or [],
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False,
        },
    }

    # Resumable upload initiation
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Upload-Content-Type": "video/*",
    }

    file_size = os.path.getsize(video_path)
    headers["X-Upload-Content-Length"] = str(file_size)

    init_response = httpx.post(
        "https://www.googleapis.com/upload/youtube/v3/videos"
        "?uploadType=resumable&part=snippet,status",
        headers=headers,
        json=metadata,
        timeout=30,
    )

    if init_response.status_code not in (200, 308):
        logger.error("youtube.upload_init_failed",
                     status=init_response.status_code,
                     body=init_response.text[:300])
        raise RuntimeError(f"YouTube upload init failed: {init_response.text[:300]}")

    upload_url = init_response.headers.get("Location")
    if not upload_url:
        raise RuntimeError("No upload URL returned from YouTube")

    # Step 2: Upload the file content
    with open(video_path, "rb") as video_file:
        upload_response = httpx.put(
            upload_url,
            content=video_file.read(),
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "video/*",
            },
            timeout=600,
        )

    if upload_response.status_code not in (200, 201):
        logger.error("youtube.upload_failed",
                     status=upload_response.status_code,
                     body=upload_response.text[:300])
        raise RuntimeError(f"YouTube upload failed: {upload_response.text[:300]}")

    result = upload_response.json()
    yt_video_id = result.get("id")

    logger.info("youtube.uploaded", video_id=yt_video_id, title=title)

    # Step 3: Upload custom thumbnail (if provided)
    if thumbnail_path and os.path.exists(thumbnail_path):
        try:
            _upload_thumbnail(access_token, yt_video_id, thumbnail_path)
        except Exception as e:
            logger.warning("youtube.thumbnail_failed", error=str(e))

    return {
        "youtube_video_id": yt_video_id,
        "url": f"https://www.youtube.com/watch?v={yt_video_id}",
        "privacy_status": privacy_status,
    }


def _upload_thumbnail(access_token: str, video_id: str, thumbnail_path: str):
    """Upload a custom thumbnail for a video."""
    with open(thumbnail_path, "rb") as thumb:
        response = httpx.post(
            f"https://www.googleapis.com/upload/youtube/v3/thumbnails/set"
            f"?videoId={video_id}",
            content=thumb.read(),
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "image/png",
            },
            timeout=30,
        )
    if response.status_code not in (200, 201):
        raise RuntimeError(f"Thumbnail upload failed: {response.text[:200]}")
    logger.info("youtube.thumbnail_uploaded", video_id=video_id)


def _load_token() -> dict | None:
    """Load stored OAuth token."""
    if not os.path.exists(TOKEN_FILE):
        return None
    with open(TOKEN_FILE, "r") as f:
        token = json.load(f)

    # Check if token needs refresh
    if _is_expired(token):
        token = _refresh_token(token)

    return token


def _is_expired(token: dict) -> bool:
    """Check if the access token is expired."""
    import time
    expires_at = token.get("expires_at", 0)
    return time.time() > expires_at - 60


def _refresh_token(token: dict) -> dict:
    """Refresh an expired OAuth token."""
    if not os.path.exists(CLIENT_SECRETS_FILE):
        raise RuntimeError("client_secrets.json not found — cannot refresh token")

    with open(CLIENT_SECRETS_FILE, "r") as f:
        secrets = json.load(f)

    client_info = secrets.get("installed") or secrets.get("web", {})

    response = httpx.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": client_info["client_id"],
            "client_secret": client_info["client_secret"],
            "refresh_token": token["refresh_token"],
            "grant_type": "refresh_token",
        },
        timeout=15,
    )

    if response.status_code != 200:
        raise RuntimeError(f"Token refresh failed: {response.text}")

    import time
    new_token = response.json()
    new_token["refresh_token"] = token.get("refresh_token")
    new_token["expires_at"] = time.time() + new_token.get("expires_in", 3600)

    with open(TOKEN_FILE, "w") as f:
        json.dump(new_token, f)

    return new_token


def authorize():
    """Interactive OAuth2 authorization flow. Run once to get token."""
    if not os.path.exists(CLIENT_SECRETS_FILE):
        print(f"ERROR: {CLIENT_SECRETS_FILE} not found.")
        print("Download OAuth2 credentials from Google Cloud Console.")
        return

    with open(CLIENT_SECRETS_FILE, "r") as f:
        secrets = json.load(f)

    client_info = secrets.get("installed") or secrets.get("web", {})
    client_id = client_info["client_id"]
    client_secret = client_info["client_secret"]

    # Step 1: Get authorization URL
    scopes = "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube"
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={client_id}"
        f"&redirect_uri=urn:ietf:wg:oauth:2.0:oob"
        f"&response_type=code"
        f"&scope={scopes}"
        f"&access_type=offline"
    )

    print(f"\nOpen this URL in your browser:\n\n{auth_url}\n")
    auth_code = input("Enter the authorization code: ").strip()

    # Step 2: Exchange code for token
    response = httpx.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": auth_code,
            "grant_type": "authorization_code",
            "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
        },
        timeout=15,
    )

    if response.status_code != 200:
        print(f"Authorization failed: {response.text}")
        return

    import time
    token = response.json()
    token["expires_at"] = time.time() + token.get("expires_in", 3600)

    with open(TOKEN_FILE, "w") as f:
        json.dump(token, f)

    print(f"\nAuthorization successful! Token saved to {TOKEN_FILE}")


if __name__ == "__main__":
    authorize()
