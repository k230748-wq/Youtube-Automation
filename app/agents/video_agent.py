"""Video Agent — assembles final video from clips + audio with transitions and polish."""

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
        sections = phase_2.get("sections", [])
        scene_clips = phase_3.get("scene_clips", [])
        audio_path = phase_4.get("audio_path", "")
        audio_duration = phase_4.get("duration_seconds", 0)

        if not scene_clips:
            raise ValueError("No scene clips from Phase 3 — cannot assemble video")
        if not audio_path:
            raise ValueError("No audio from Phase 4 — cannot assemble video")

        logger.info("video.start", title=title, scenes=len(scene_clips),
                     audio_duration=audio_duration)

        from app.utils.file_manager import get_video_dir
        video_dir = get_video_dir(pipeline_run_id)

        # Step 1: Download best clip per scene
        downloaded_clips = self._download_clips(scene_clips, video_dir)

        # Step 2: Normalize clips (scale, color grade, trim to scene duration)
        prepared_clips = self._prepare_clips(
            downloaded_clips, audio_duration, video_dir
        )

        # Step 3: Stitch with crossfade transitions
        raw_video = self._stitch_with_transitions(prepared_clips, video_dir)

        # Step 4: Add narration audio (with background music if configured)
        music_path = config.get("background_music_path")
        if music_path and os.path.exists(music_path):
            video_with_audio = self._add_audio_with_music(
                raw_video, audio_path, music_path, video_dir,
                music_volume=config.get("music_volume", 0.12),
            )
        else:
            video_with_audio = self._add_audio(raw_video, audio_path, video_dir)

        # Step 5: Add fade in/out
        final_video = self._add_fades(video_with_audio, video_dir)

        # Step 6: Update video record
        self._update_video_record(video_id, final_video)

        result = {
            "video_id": video_id,
            "video_path": final_video,
            "duration_seconds": audio_duration,
            "clips_used": len(downloaded_clips),
            "title": title,
        }

        logger.info("video.complete", video_path=final_video)
        return result

    def _download_clips(self, scene_clips: list, video_dir: str) -> list:
        """Download the best stock clip per scene."""
        from app.integrations.ffmpeg_client import download_clip

        clips_dir = os.path.join(video_dir, "clips")
        os.makedirs(clips_dir, exist_ok=True)

        downloaded = []
        for i, scene in enumerate(scene_clips):
            clips = scene.get("clips", [])
            if not clips:
                logger.warning("video.no_clips_for_scene", scene=i)
                continue

            # Score and pick best clip
            best_clip = self._pick_best_clip(clips, scene.get("duration_needed", 10))
            url = best_clip.get("url")
            if not url:
                continue

            clip_path = os.path.join(clips_dir, f"scene_{i:03d}.mp4")
            try:
                download_clip(url, clip_path)
                downloaded.append({
                    "path": clip_path,
                    "scene_number": scene.get("scene_number", i),
                    "duration_needed": scene.get("duration_needed", 10),
                    "source": best_clip.get("source"),
                })
                logger.info("video.clip_downloaded", scene=i,
                           source=best_clip.get("source"))
            except Exception as e:
                logger.warning("video.clip_download_failed", scene=i,
                             url=url, error=str(e))

        return downloaded

    def _pick_best_clip(self, clips: list, duration_needed: float) -> dict:
        """Score clips and return the best one."""
        if not clips:
            return {}

        scored = []
        for clip in clips:
            score = 0.0
            clip_dur = clip.get("duration") or 10

            # Duration match (prefer clips close to needed duration)
            dur_diff = abs(clip_dur - duration_needed)
            if dur_diff < 3:
                score += 10
            elif dur_diff < 8:
                score += 5
            else:
                score += max(0, 10 - dur_diff)

            # Prefer HD quality
            if clip.get("quality") == "hd":
                score += 5

            # Prefer Pexels (generally higher quality)
            if clip.get("source") == "pexels":
                score += 2

            scored.append((score, clip))

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1]

    def _prepare_clips(self, downloaded_clips: list, total_audio_duration: float,
                       video_dir: str) -> list:
        """Normalize clips: scale to 1080p, color grade, trim to scene duration."""
        from app.integrations.ffmpeg_client import normalize_clip

        prepared = []
        prep_dir = os.path.join(video_dir, "prepared")
        os.makedirs(prep_dir, exist_ok=True)

        num_clips = len(downloaded_clips)
        if num_clips == 0:
            return []

        # Distribute audio duration across clips proportionally
        total_needed = sum(c.get("duration_needed", 10) for c in downloaded_clips)

        for i, clip in enumerate(downloaded_clips):
            needed = clip.get("duration_needed", 10)
            target_duration = (needed / total_needed) * total_audio_duration \
                if total_needed > 0 else total_audio_duration / num_clips

            # Clamp: min 2s, max 15s per clip (avoids boring long holds)
            target_duration = max(2.0, min(15.0, target_duration))

            input_path = clip["path"]
            output_path = os.path.join(prep_dir, f"prep_{i:03d}.mp4")

            try:
                normalize_clip(
                    input_path, output_path,
                    target_duration=target_duration,
                    color_grade=True,
                )
                prepared.append(output_path)
            except Exception as e:
                logger.warning("video.prepare_error", clip=i, error=str(e))

        return prepared

    def _stitch_with_transitions(self, clip_paths: list, video_dir: str) -> str:
        """Stitch clips with crossfade transitions."""
        from app.integrations.ffmpeg_client import stitch_with_crossfade

        output_path = os.path.join(video_dir, "raw_video.mp4")

        if not clip_paths:
            raise ValueError("No clips to stitch — all downloads/preparations failed")

        return stitch_with_crossfade(
            clip_paths, output_path,
            transition="fade",
            duration=0.5,
        )

    def _add_audio(self, video_path: str, audio_path: str, video_dir: str) -> str:
        """Add narration audio to the stitched video."""
        from app.integrations.ffmpeg_client import add_audio

        output_path = os.path.join(video_dir, "video_with_audio.mp4")
        add_audio(video_path, audio_path, output_path)
        return output_path

    def _add_audio_with_music(self, video_path: str, audio_path: str,
                               music_path: str, video_dir: str,
                               music_volume: float = 0.12) -> str:
        """Add narration + background music with auto-ducking."""
        from app.integrations.ffmpeg_client import add_audio_with_background_music

        output_path = os.path.join(video_dir, "video_with_audio.mp4")
        return add_audio_with_background_music(
            video_path, audio_path, music_path, output_path,
            music_volume=music_volume,
        )

    def _add_fades(self, video_path: str, video_dir: str) -> str:
        """Add fade from black at start, fade to black at end."""
        from app.integrations.ffmpeg_client import add_fade_in_out

        output_path = os.path.join(video_dir, "final_video.mp4")
        return add_fade_in_out(
            video_path, output_path,
            fade_in=1.0, fade_out=1.5,
        )

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
