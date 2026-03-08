"""FFmpeg integration — video assembly, transitions, overlays, styling."""

import os
import subprocess
import structlog

logger = structlog.get_logger(__name__)


def stitch_clips(clip_paths: list, output_path: str) -> str:
    """Concatenate video clips into a single video (hard cuts)."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

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
        logger.error("ffmpeg.stitch.failed", stderr=result.stderr[:300])
        raise RuntimeError(f"FFmpeg stitch failed: {result.stderr[:300]}")

    return output_path


def stitch_with_crossfade(clip_paths: list, output_path: str,
                          transition: str = "fade",
                          duration: float = 0.5) -> str:
    """Concatenate clips with crossfade transitions between them."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    if len(clip_paths) < 2:
        if clip_paths:
            import shutil
            shutil.copy2(clip_paths[0], output_path)
        return output_path

    # Get durations for all clips
    durations = []
    for cp in clip_paths:
        try:
            dur = get_duration(cp)
            durations.append(dur)
        except Exception:
            durations.append(5.0)

    # Build xfade filter chain
    input_args = []
    for cp in clip_paths:
        input_args.extend(["-i", cp])

    filters = []
    running_duration = durations[0]

    for i in range(1, len(clip_paths)):
        offset = max(0, running_duration - duration)
        in_label = f"[{i-1}:v]" if i == 1 else f"[xf{i-2}]"
        out_label = f"[xf{i-1}]"

        filters.append(
            f"{in_label}[{i}:v]xfade=transition={transition}"
            f":duration={duration}:offset={offset}{out_label}"
        )
        running_duration += durations[i] - duration

    filter_complex = "; ".join(filters)
    final_label = f"[xf{len(clip_paths)-2}]"

    cmd = [
        "ffmpeg", "-y",
        *input_args,
        "-filter_complex", filter_complex,
        "-map", final_label,
        "-c:v", "libx264", "-preset", "fast",
        "-pix_fmt", "yuv420p",
        "-r", "30",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

    if result.returncode != 0:
        logger.warning("ffmpeg.xfade_failed_fallback_concat",
                       stderr=result.stderr[:200])
        return stitch_clips(clip_paths, output_path)

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
        logger.error("ffmpeg.add_audio.failed", stderr=result.stderr[:300])
        raise RuntimeError(f"FFmpeg add audio failed: {result.stderr[:300]}")

    return output_path


def add_audio_with_background_music(video_path: str, narration_path: str,
                                    music_path: str, output_path: str,
                                    music_volume: float = 0.12) -> str:
    """Add narration + background music with auto-ducking."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", narration_path,
        "-i", music_path,
        "-filter_complex",
        f"[1:a]volume=1.0[voice];"
        f"[2:a]volume={music_volume}[music_raw];"
        f"[voice][music_raw]amix=inputs=2:duration=first:dropout_transition=3[aout]",
        "-map", "0:v",
        "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        logger.warning("ffmpeg.bg_music_failed_using_narration_only",
                       stderr=result.stderr[:200])
        return add_audio(video_path, narration_path, output_path)

    return output_path


def add_subtitles_styled(video_path: str, srt_path: str, output_path: str,
                         font: str = "Sans", fontsize: int = 24,
                         style: str = "box") -> str:
    """Burn styled subtitles into a video.

    Styles:
      - 'box': white text with semi-transparent black box background
      - 'outline': white text with thick black outline (no box)
      - 'bold': large bold white text with outline, centered
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    style_map = {
        "box": (
            f"Fontname={font},"
            f"Fontsize={fontsize},"
            "PrimaryColour=&H00FFFFFF,"
            "OutlineColour=&H40000000,"
            "BackColour=&H80000000,"
            "BorderStyle=4,"
            "Outline=1,"
            "Shadow=0,"
            "MarginV=35,"
            "Bold=1"
        ),
        "outline": (
            f"Fontname={font},"
            f"Fontsize={fontsize},"
            "PrimaryColour=&H00FFFFFF,"
            "OutlineColour=&H00000000,"
            "BorderStyle=1,"
            "Outline=3,"
            "Shadow=1,"
            "MarginV=35,"
            "Bold=1"
        ),
        "bold": (
            f"Fontname={font},"
            f"Fontsize={int(fontsize * 1.5)},"
            "PrimaryColour=&H00FFFFFF,"
            "OutlineColour=&H00000000,"
            "BorderStyle=1,"
            "Outline=3,"
            "Shadow=0,"
            "Alignment=10,"
            "MarginV=40,"
            "Bold=1"
        ),
        "minimal": (
            f"Fontname={font},"
            f"Fontsize={int(fontsize * 0.75)},"
            "PrimaryColour=&H00FFFFFF,"
            "OutlineColour=&H50000000,"
            "BackColour=&H00000000,"
            "BorderStyle=1,"
            "Outline=1,"
            "Shadow=0,"
            "MarginV=25,"
            "Bold=0,"
            "Spacing=0.5"
        ),
    }

    force_style = style_map.get(style, style_map["outline"])

    # Escape the SRT path for FFmpeg (colons and backslashes)
    escaped_srt = srt_path.replace("\\", "/").replace(":", "\\:")

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", f"subtitles={escaped_srt}:force_style='{force_style}'",
        "-c:a", "copy",
        "-c:v", "libx264", "-preset", "fast",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

    if result.returncode != 0:
        logger.warning("ffmpeg.styled_subs_failed_trying_basic",
                       stderr=result.stderr[:200])
        return add_subtitles(video_path, srt_path, output_path)

    return output_path


def add_subtitles(video_path: str, srt_path: str, output_path: str) -> str:
    """Burn subtitles into a video (basic fallback)."""
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
        logger.error("ffmpeg.subtitles.failed", stderr=result.stderr[:300])
        raise RuntimeError(f"FFmpeg subtitles failed: {result.stderr[:300]}")

    return output_path


def normalize_clip(input_path: str, output_path: str,
                   target_duration: float = None,
                   width: int = 1920, height: int = 1080,
                   fps: int = 30,
                   color_grade: bool = True) -> str:
    """Normalize a clip: scale, pad, trim, optional color grading."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    vf_filters = [
        f"scale={width}:{height}:force_original_aspect_ratio=decrease",
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
    ]

    if color_grade:
        # Subtle color grading: slight brightness + contrast + saturation
        vf_filters.append("eq=brightness=0.03:contrast=1.06:saturation=1.12")
        # Gentle vignette for unified look
        vf_filters.append("vignette=PI/5")

    vf = ",".join(vf_filters)

    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
    ]

    if target_duration:
        cmd.extend(["-t", str(target_duration)])

    cmd.extend([
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast",
        "-an",
        "-r", str(fps),
        "-pix_fmt", "yuv420p",
        output_path,
    ])

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    if result.returncode != 0:
        logger.error("ffmpeg.normalize.failed", stderr=result.stderr[:300])
        raise RuntimeError(f"FFmpeg normalize failed: {result.stderr[:300]}")

    return output_path


def add_fade_in_out(video_path: str, output_path: str,
                    fade_in: float = 1.0, fade_out: float = 1.5) -> str:
    """Add fade from black at start and fade to black at end."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    duration = get_duration(video_path)
    fade_out_start = max(0, duration - fade_out)

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", f"fade=t=in:st=0:d={fade_in},fade=t=out:st={fade_out_start}:d={fade_out}",
        "-af", f"afade=t=in:st=0:d={fade_in},afade=t=out:st={fade_out_start}:d={fade_out}",
        "-c:v", "libx264", "-preset", "fast",
        "-c:a", "aac",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        logger.warning("ffmpeg.fade_failed", stderr=result.stderr[:200])
        import shutil
        shutil.copy2(video_path, output_path)

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


def image_to_video(image_path: str, output_path: str,
                    duration: float = 5.0,
                    width: int = 1920, height: int = 1080,
                    fps: int = 30,
                    zoom: bool = True,
                    effect: str = "slow_zoom_in") -> str:
    """Convert a still image to a video clip with Ken Burns effects.

    Effects:
      - slow_zoom_in: gentle zoom from 1.0x to 1.06x (centered)
      - slow_zoom_out: start at 1.06x, pull back to 1.0x (centered)
      - pan_left: slow horizontal pan from right to left at 1.03x
      - pan_right: slow horizontal pan from left to right at 1.03x
      - zoom_to_center: more dramatic zoom from 1.0x to 1.10x (centered)
      - static: no movement

    When zoom=False: static frame regardless of effect.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    if zoom and effect != "static":
        total_frames = int(duration * fps)

        if effect == "slow_zoom_out":
            z_expr = f"1.06-0.06/{total_frames}*on"
            x_expr = "iw/2-(iw/zoom/2)"
            y_expr = "ih/2-(ih/zoom/2)"
        elif effect == "pan_left":
            z_expr = "1.03"
            x_expr = f"(iw-iw/zoom)*({total_frames}-on)/{total_frames}"
            y_expr = "ih/2-(ih/zoom/2)"
        elif effect == "pan_right":
            z_expr = "1.03"
            x_expr = f"(iw-iw/zoom)*on/{total_frames}"
            y_expr = "ih/2-(ih/zoom/2)"
        elif effect == "zoom_to_center":
            z_expr = f"1+0.10/{total_frames}*on"
            x_expr = "iw/2-(iw/zoom/2)"
            y_expr = "ih/2-(ih/zoom/2)"
        else:  # slow_zoom_in (default)
            z_expr = f"1+0.06/{total_frames}*on"
            x_expr = "iw/2-(iw/zoom/2)"
            y_expr = "ih/2-(ih/zoom/2)"

        zoompan = (
            f"zoompan=z='{z_expr}':x='{x_expr}':y='{y_expr}'"
            f":d={total_frames}:s={width}x{height}:fps={fps}"
        )
        vf = f"scale=3840:2160:flags=lanczos,{zoompan}"
    else:
        vf = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black"

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", image_path,
        "-vf", vf,
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "fast",
        "-pix_fmt", "yuv420p",
        "-r", str(fps),
        "-an",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)

    if result.returncode != 0:
        logger.error("ffmpeg.image_to_video.failed", stderr=result.stderr[:300])
        raise RuntimeError(f"FFmpeg image_to_video failed: {result.stderr[:300]}")

    return output_path


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
