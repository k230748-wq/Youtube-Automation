"""FFmpeg integration — video assembly, stitching, overlays."""

import os
import subprocess
import structlog

logger = structlog.get_logger(__name__)


def stitch_clips(clip_paths: list, output_path: str) -> str:
    """Concatenate video clips into a single video."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Create concat file
    concat_file = output_path.replace(".mp4", "_concat.txt")
    with open(concat_file, "w") as f:
        for clip in clip_paths:
            f.write(f"file '{os.path.abspath(clip)}'\n")

    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_file,
        "-c", "copy",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    os.remove(concat_file)

    if result.returncode != 0:
        logger.error("ffmpeg.stitch.failed", stderr=result.stderr)
        raise RuntimeError(f"FFmpeg stitch failed: {result.stderr}")

    return output_path


def add_audio(video_path: str, audio_path: str, output_path: str) -> str:
    """Add audio track to a video."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", audio_path,
        "-c:v", "copy",
        "-c:a", "aac",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-shortest",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        logger.error("ffmpeg.add_audio.failed", stderr=result.stderr)
        raise RuntimeError(f"FFmpeg add audio failed: {result.stderr}")

    return output_path


def add_subtitles(video_path: str, srt_path: str, output_path: str) -> str:
    """Burn subtitles into a video."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", f"subtitles={srt_path}",
        "-c:a", "copy",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

    if result.returncode != 0:
        logger.error("ffmpeg.subtitles.failed", stderr=result.stderr)
        raise RuntimeError(f"FFmpeg subtitles failed: {result.stderr}")

    return output_path


def get_duration(file_path: str) -> float:
    """Get duration of a video/audio file in seconds."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"FFprobe failed: {result.stderr}")
    return float(result.stdout.strip())


def download_clip(url: str, output_path: str) -> str:
    """Download a video clip from URL."""
    import httpx
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with httpx.stream("GET", url, timeout=60, follow_redirects=True) as response:
        response.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in response.iter_bytes():
                f.write(chunk)
    return output_path
