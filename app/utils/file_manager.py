"""File and asset management utilities."""

import os
import json
from config.settings import settings


def get_video_dir(pipeline_run_id: str, video_id: str = None) -> str:
    """Get or create the directory for a video's assets."""
    base = os.path.join(settings.ASSETS_DIR, pipeline_run_id)
    if video_id:
        base = os.path.join(base, video_id)
    os.makedirs(base, exist_ok=True)
    return base


def save_json(filepath: str, data: dict):
    """Save data as JSON file."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, default=str)


def load_json(filepath: str) -> dict:
    """Load data from JSON file."""
    with open(filepath, "r") as f:
        return json.load(f)


def save_text(filepath: str, content: str):
    """Save text content to file."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        f.write(content)


def save_binary(filepath: str, data: bytes):
    """Save binary content (audio, video) to file."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "wb") as f:
        f.write(data)


def list_assets(pipeline_run_id: str) -> list:
    """List all assets for a pipeline run."""
    base = os.path.join(settings.ASSETS_DIR, pipeline_run_id)
    if not os.path.exists(base):
        return []

    assets = []
    for root, dirs, files in os.walk(base):
        for f in files:
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, settings.ASSETS_DIR)
            assets.append({
                "path": rel_path,
                "name": f,
                "size": os.path.getsize(full_path),
            })

    return assets
