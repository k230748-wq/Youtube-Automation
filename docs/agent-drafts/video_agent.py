"""Video Agent — assembles final video from clips + audio using FFmpeg."""

import os
import structlog

from app.agents.base import BaseAgent

logger = structlog.get_logger(__name__)


class VideoAgent(BaseAgent):
    agent_name = "video_agent"
    phase_number = 5

    def run(self, input_data: dict, learning_context: list) -> dict:
        pipeline_run_id = input_data.get("pipeline_run_id", "")
        config = input_data.get("pipeline_config", {})

        # Get data from previous phases
        phase_2 = input_data.get("phase_2_output", {})
        phase_3 = input_data.get("phase_3_output", {})
        phase_4 = input_data.get("phase_4_output", {})

        title = phase_2.get("selected_title", "")
        video_id = phase_2.get("video_id")
        scene_clips = phase_3.get("scene_clips", [])
        audio_path = phase_4.get("audio_path", "")
        audio_duration = phase_4.get("duration_seconds", 0)

        if not scene_clips:
            raise ValueError("No scene clips from Phase 3 — cannot assemble video")
        if not audio_path:
            raise ValueError("No audio from Phase 4 — cannot assemble video")

        logger.info("video.start", title=title, scenes=len(scene_clips), audio_duration=audio_duration)

        from app.utils.file_manager import get_video_dir
        video_dir = get_video_dir(pipeline_run_id)

        # Step 1: Download all stock clips
        downloaded_clips = self._download_clips(scene_clips, video_dir)

        # Step 2: Trim/loop clips to match scene durations
        prepared_clips = self._prepare_clips(downloaded_clips, scene_clips, audio_duration, video_dir)

        # Step 3: Concatenate all clips into one video
        raw_video = self._stitch_video(prepared_clips, video_dir)

        # Step 4: Add audio track
        video_with_audio = self._add_audio(raw_video, audio_path, video_dir)

        # Step 5: Update video record
        self._update_video_record(video_id, video_with_audio)

        result = {
            "video_id": video_id,
            "video_path": video_with_audio,
            "duration_seconds": audio_duration,
            "clips_used": len(downloaded_clips),
            "title": title,
        }

        logger.info("video.complete", video_path=video_with_audio)
        return result

    def _download_clips(self, scene_clips: list, video_dir: str) -> list:
        """Download stock video clips from URLs."""
        from app.integrations.ffmpeg_client import download_clip

        clips_dir = os.path.join(video_dir, "clips")
        os.makedirs(clips_dir, exist_ok=True)

        downloaded = []
        for i, scene in enumerate(scene_clips):
            clips = scene.get("clips", [])
            if not clips:
                logger.warning("video.no_clips_for_scene", scene=i)
                continue

            # Use the first available clip
            clip = clips[0]
            url = clip.get("url")
            if not url:
                continue

            clip_path = os.path.join(clips_dir, f"scene_{i:03d}.mp4")
            try:
                download_clip(url, clip_path)
                downloaded.append({
                    "path": clip_path,
                    "scene_number": scene.get("scene_number", i),
                    "duration_needed": scene.get("duration_needed", 30),
                    "source": clip.get("source"),
                })
                logger.info("video.clip_downloaded", scene=i, source=clip.get("source"))
            except Exception as e:
                logger.warning("video.clip_download_failed", scene=i, url=url, error=str(e))

        return downloaded

    def _prepare_clips(self, downloaded_clips: list, scene_clips: list, total_audio_duration: float, video_dir: str) -> list:
        """Trim or loop clips to match required scene durations."""
        import subprocess

        prepared = []
        prep_dir = os.path.join(video_dir, "prepared")
        os.makedirs(prep_dir, exist_ok=True)

        # Calculate duration per clip based on audio length
        num_clips = len(downloaded_clips)
        if num_clips == 0:
            return []

        # Distribute audio duration across clips proportionally
        total_needed = sum(c.get("duration_needed", 30) for c in downloaded_clips)

        for i, clip in enumerate(downloaded_clips):
            needed = clip.get("duration_needed", 30)
            # Scale to actual audio duration
            target_duration = (needed / total_needed) * total_audio_duration if total_needed > 0 else total_audio_duration / num_clips

            input_path = clip["path"]
            output_path = os.path.join(prep_dir, f"prep_{i:03d}.mp4")

            try:
                # Normalize video: scale to 1920x1080, trim to target duration
                cmd = [
                    "ffmpeg", "-y",
                    "-i", input_path,
                    "-t", str(target_duration),
                    "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
                    "-c:v", "libx264", "-preset", "fast",
                    "-an",  # strip any existing audio
                    "-r", "30",
                    output_path,
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

                if result.returncode == 0:
                    prepared.append(output_path)
                else:
                    logger.warning("video.prepare_failed", clip=i, stderr=result.stderr[:200])
            except Exception as e:
                logger.warning("video.prepare_error", clip=i, error=str(e))

        return prepared

    def _stitch_video(self, clip_paths: list, video_dir: str) -> str:
        """Concatenate prepared clips into one video."""
        from app.integrations.ffmpeg_client import stitch_clips

        output_path = os.path.join(video_dir, "raw_video.mp4")

        if not clip_paths:
            raise ValueError("No clips to stitch — all downloads/preparations failed")

        # FFmpeg concat requires same codec/resolution — we normalized in _prepare_clips
        concat_file = os.path.join(video_dir, "concat_list.txt")
        with open(concat_file, "w") as f:
            for cp in clip_paths:
                f.write(f"file '{os.path.abspath(cp)}'\n")

        import subprocess
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", concat_file,
            "-c", "copy",
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        os.remove(concat_file)

        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg stitch failed: {result.stderr[:300]}")

        return output_path

    def _add_audio(self, video_path: str, audio_path: str, video_dir: str) -> str:
        """Add narration audio to the stitched video."""
        from app.integrations.ffmpeg_client import add_audio

        output_path = os.path.join(video_dir, "final_video.mp4")
        add_audio(video_path, audio_path, output_path)
        return output_path

    def _update_video_record(self, video_id: str, video_path: str):
        """Update the Video record with final video path."""
        if not video_id:
            return
        try:
            from app import db
            from app.models.video import Video

            video = Video.query.get(video_id)
            if video:
                video.final_video_path = video_path
                video.status = "processing"
                db.session.commit()
        except Exception as e:
            logger.warning("video.update_record_failed", error=str(e))
