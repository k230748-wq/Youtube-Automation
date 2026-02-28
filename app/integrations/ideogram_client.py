"""Ideogram API integration — AI image generation for covers and ad creatives.

Supports both the legacy V2 endpoint and the Ideogram 3.0 (V3) endpoint.

Legacy (V2):  POST https://api.ideogram.ai/generate
  - Content-Type: application/json
  - Body: {"image_request": {...}}
  - aspect_ratio enum: ASPECT_<W>_<H>  (e.g. ASPECT_2_3)
  - model enum: V_1, V_1_TURBO, V_2, V_2_TURBO, V_2A, V_2A_TURBO, AUTO
  - style_type enum: AUTO, GENERAL, REALISTIC, DESIGN, FICTION, RENDER_3D, ANIME

V3:  POST https://api.ideogram.ai/v1/ideogram-v3/generate
  - Content-Type: multipart/form-data  (form fields, not JSON)
  - aspect_ratio enum: <W>x<H>  (e.g. 2x3)
  - rendering_speed enum: FLASH, TURBO, DEFAULT, QUALITY
  - style_type enum: AUTO, GENERAL, REALISTIC, DESIGN, FICTION
  - magic_prompt enum: AUTO, ON, OFF
"""

import httpx
from config.settings import settings

BASE_URL = "https://api.ideogram.ai"

# ---------------------------------------------------------------------------
# Aspect-ratio helpers
# ---------------------------------------------------------------------------
# Legacy V2 uses "ASPECT_W_H"; V3 uses "WxH".
VALID_V2_ASPECT_RATIOS = {
    "ASPECT_10_16", "ASPECT_16_10", "ASPECT_9_16", "ASPECT_16_9",
    "ASPECT_3_2", "ASPECT_2_3", "ASPECT_4_3", "ASPECT_3_4",
    "ASPECT_1_1", "ASPECT_1_3", "ASPECT_3_1",
}

VALID_V3_ASPECT_RATIOS = {
    "1x3", "3x1", "1x2", "2x1", "9x16", "16x9", "10x16", "16x10",
    "2x3", "3x2", "3x4", "4x3", "4x5", "5x4", "1x1",
}


def _normalise_aspect_ratio_v2(raw: str) -> str:
    """Convert user-friendly ratio strings to the V2 enum value.

    Accepts formats like "2:3", "2_3", "2x3", or "ASPECT_2_3".
    """
    cleaned = raw.strip().upper()
    if cleaned.startswith("ASPECT_"):
        return cleaned  # already in canonical form
    # Normalise common separators to underscore
    for sep in (":", "x", "X", "/"):
        cleaned = cleaned.replace(sep, "_")
    return f"ASPECT_{cleaned}"


def _normalise_aspect_ratio_v3(raw: str) -> str:
    """Convert user-friendly ratio strings to the V3 enum value (WxH)."""
    cleaned = raw.strip().lower()
    for sep in (":", "_", "/"):
        cleaned = cleaned.replace(sep, "x")
    if cleaned.startswith("aspect_"):
        cleaned = cleaned.replace("aspect_", "").replace("_", "x")
    return cleaned


# ---------------------------------------------------------------------------
# Legacy V2 generate
# ---------------------------------------------------------------------------
def generate_image(
    prompt: str,
    aspect_ratio: str = "1:1",
    style: str = "DESIGN",
    negative_prompt: str = "",
    model: str = "V_2",
    num_images: int = 1,
) -> dict:
    """Generate an image using the Ideogram *legacy* V2 endpoint.

    Parameters
    ----------
    prompt : str
        Text description of the desired image.
    aspect_ratio : str
        Any common format — "2:3", "2x3", "ASPECT_2_3" etc.
    style : str
        One of AUTO, GENERAL, REALISTIC, DESIGN, FICTION, RENDER_3D, ANIME.
    negative_prompt : str
        Content to exclude from the generated image.
    model : str
        Model version: V_1, V_1_TURBO, V_2, V_2_TURBO, V_2A, V_2A_TURBO, AUTO.
    num_images : int
        Number of images to generate (default 1).
    """
    ar = _normalise_aspect_ratio_v2(aspect_ratio)

    response = httpx.post(
        f"{BASE_URL}/generate",
        headers={
            "Api-Key": settings.IDEOGRAM_API_KEY,
            "Content-Type": "application/json",
        },
        json={
            "image_request": {
                "prompt": prompt,
                "aspect_ratio": ar,
                "model": model,
                "style_type": style.upper(),
                "negative_prompt": negative_prompt,
                "num_images": num_images,
            },
        },
        timeout=120,
    )
    response.raise_for_status()
    data = response.json()

    images = data.get("data", [])
    if images:
        return {
            "url": images[0].get("url"),
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
        }

    return {"error": "No images generated", "prompt": prompt}


# ---------------------------------------------------------------------------
# Ideogram 3.0 (V3) generate
# ---------------------------------------------------------------------------
def generate_image_v3(
    prompt: str,
    aspect_ratio: str = "1x1",
    style_type: str = "GENERAL",
    negative_prompt: str = "",
    rendering_speed: str = "DEFAULT",
    magic_prompt: str = "AUTO",
    num_images: int = 1,
) -> dict:
    """Generate an image using the Ideogram 3.0 (V3) endpoint.

    The V3 endpoint uses multipart/form-data (not JSON).

    Parameters
    ----------
    prompt : str
        Text description of the desired image.
    aspect_ratio : str
        Format "WxH" — e.g. "2x3", "16x9", "1x1".
    style_type : str
        One of AUTO, GENERAL, REALISTIC, DESIGN, FICTION.
    negative_prompt : str
        Content to exclude.
    rendering_speed : str
        One of FLASH, TURBO, DEFAULT, QUALITY.
    magic_prompt : str
        One of AUTO, ON, OFF.
    num_images : int
        Number of images to generate (default 1).
    """
    ar = _normalise_aspect_ratio_v3(aspect_ratio)

    form_data = {
        "prompt": prompt,
        "aspect_ratio": ar,
        "style_type": style_type.upper(),
        "rendering_speed": rendering_speed.upper(),
        "magic_prompt": magic_prompt.upper(),
        "num_images": str(num_images),
    }
    if negative_prompt:
        form_data["negative_prompt"] = negative_prompt

    response = httpx.post(
        f"{BASE_URL}/v1/ideogram-v3/generate",
        headers={
            "Api-Key": settings.IDEOGRAM_API_KEY,
        },
        data=form_data,
        timeout=120,
    )
    response.raise_for_status()
    data = response.json()

    images = data.get("data", [])
    if images:
        return {
            "url": images[0].get("url"),
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
        }

    return {"error": "No images generated", "prompt": prompt}
