"""Video Agent — assembles final video from clips + audio with transitions and polish."""

import os
import structlog

from app.agents.base import BaseAgent

logger = structlog.get_logger(__name__)


class VideoAgent(BaseAgent):
    agent_name = "video_agent"
    phase_number = 6

    def run(self, input_data: dict, learning_context: list) -> dict:
        pipeline_run_id = input_data.get("pipeline_run_id", "")
        config = input_data.get("pipeline_config", {})

        # Get data from previous phases
        phase_2 = input_data.get("phase_2_output", {})
        phase_3 = input_data.get("phase_3_output", {})  # Voice
        phase_5 = input_data.get("phase_5_output", {})  # Media (was phase_4)

        title = phase_2.get("selected_title", "")
        video_id = phase_2.get("video_id")
        sections = phase_2.get("sections", [])

        # Phase 3 is Voice
        audio_path = phase_3.get("audio_path", "")
        audio_duration = phase_3.get("duration_seconds", 0)

        # Phase 5 is Media (was Phase 4)
        scene_clips = phase_5.get("scene_clips", [])

        if not scene_clips:
            raise ValueError("No scene clips from Phase 5 — cannot assemble video")
        if not audio_path:
            raise ValueError("No audio from Phase 3 — cannot assemble video")

        logger.info("video.start", title=title, scenes=len(scene_clips),
                     audio_duration=audio_duration)

        from app.utils.file_manager import get_video_dir
        video_dir = get_video_dir(pipeline_run_id)

        # Step 1: Download best clip per scene
        downloaded_clips = self._download_clips(scene_clips, video_dir)

        # Step 2: Normalize clips (scale, color grade, trim to scene duration)
        mode = config.get("mode", "hybrid")
        prepared_clips = self._prepare_clips(
            downloaded_clips, audio_duration, video_dir,
            zoom=True,  # Always enable Ken Burns (story mode uses per-scene effects)
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
        """Download the best stock clip per scene, or use local AI images."""
        from app.integrations.ffmpeg_client import download_clip

        clips_dir = os.path.join(video_dir, "clips")
        os.makedirs(clips_dir, exist_ok=True)

        downloaded = []
        for i, scene in enumerate(scene_clips):
            clips = scene.get("clips", [])
            if not clips:
                logger.warning("video.no_clips_for_scene", scene=i)
                continue

            # AI image scenes: use local_path directly (already downloaded by media agent)
            if scene.get("media_type") == "ai_image":
                local_path = clips[0].get("local_path")
                if local_path and os.path.exists(local_path):
                    downloaded.append({
                        "path": local_path,
                        "type": "image",
                        "scene_number": scene.get("scene_number", i),
                        "duration_needed": scene.get("duration_needed", 10),
                        "source": clips[0].get("source", "ideogram"),
                        "effect": scene.get("effect", "slow_zoom_in"),
                        "narration_text": scene.get("narration_text", ""),
                        "start_time": scene.get("start_time"),     # NEW
                        "end_time": scene.get("end_time"),         # NEW
                    })
                    logger.info("video.ai_image_ready", scene=i)
                else:
                    logger.warning("video.ai_image_missing", scene=i, path=local_path)
                continue

            # Stock video scenes: download best clip
            best_clip = self._pick_best_clip(clips, scene.get("duration_needed", 10))
            url = best_clip.get("url")
            if not url:
                continue

            clip_path = os.path.join(clips_dir, f"scene_{i:03d}.mp4")
            try:
                download_clip(url, clip_path)
                downloaded.append({
                    "path": clip_path,
                    "type": "video",
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
                       video_dir: str, zoom: bool = True) -> list:
        """Normalize clips: scale to 1080p, color grade, trim to scene duration.
        AI image clips get Ken Burns zoompan effect with per-scene effects.
        Story mode uses narration-anchor timing; hybrid uses proportional scaling."""
        from app.integrations.ffmpeg_client import normalize_clip, image_to_video

        prepared = []
        prep_dir = os.path.join(video_dir, "prepared")
        os.makedirs(prep_dir, exist_ok=True)

        num_clips = len(downloaded_clips)
        if num_clips == 0:
            return []

        # Check if we have locked timing (audio-first architecture)
        has_locked_timing = all(
            c.get("start_time") is not None and c.get("end_time") is not None
            for c in downloaded_clips
        )

        if has_locked_timing:
            # Use exact timestamps from segmenter
            clips_with_duration = self._use_locked_timings(downloaded_clips)
        elif all(c.get("narration_text") for c in downloaded_clips):
            # Legacy: estimate from character count
            clips_with_duration = self._compute_anchor_timings(
                downloaded_clips, total_audio_duration)
        else:
            # Fallback: proportional scaling
            clips_with_duration = self._compute_proportional_timings(
                downloaded_clips, total_audio_duration, zoom)

        for i, clip in enumerate(clips_with_duration):
            target_duration = clip.get("target_duration", 10)
            input_path = clip["path"]
            output_path = os.path.join(prep_dir, f"prep_{i:03d}.mp4")

            try:
                if clip.get("type") == "image":
                    # AI image → video with Ken Burns effect
                    effect = clip.get("effect", "slow_zoom_in")
                    image_to_video(
                        input_path, output_path,
                        duration=target_duration,
                        zoom=zoom,
                        effect=effect,
                    )
                else:
                    # Stock video → normalize (scale, color grade, trim)
                    normalize_clip(
                        input_path, output_path,
                        target_duration=target_duration,
                        color_grade=True,
                    )
                prepared.append(output_path)
            except Exception as e:
                logger.warning("video.prepare_error", clip=i, error=str(e))

        return prepared

    def _compute_anchor_timings(self, clips: list, total_audio_duration: float) -> list:
        """Compute per-clip durations by mapping narration_text positions to audio time.
        Character count maps linearly to TTS speaking time (roughly constant chars/second)."""
        # Build full script by concatenating all narration_text in order
        full_text = ""
        clip_text_ranges = []
        for clip in clips:
            text = clip.get("narration_text", "")
            start_char = len(full_text)
            full_text += text + " "
            end_char = len(full_text)
            clip_text_ranges.append((start_char, end_char))

        total_chars = len(full_text)
        if total_chars == 0:
            # Fallback: equal distribution
            dur = total_audio_duration / len(clips)
            return [{**c, "target_duration": max(3.0, dur)} for c in clips]

        crossfade_duration = 0.5
        crossfade_loss = (len(clips) - 1) * crossfade_duration
        effective_duration = total_audio_duration + crossfade_loss

        result = []
        for i, clip in enumerate(clips):
            start_char, end_char = clip_text_ranges[i]
            # Map character position to time position (linear approximation)
            start_time = (start_char / total_chars) * effective_duration
            end_time = (end_char / total_chars) * effective_duration
            target_duration = max(3.0, min(18.0, end_time - start_time))
            result.append({**clip, "target_duration": target_duration})

        return result

    def _compute_proportional_timings(self, clips: list,
                                       total_audio_duration: float,
                                       zoom: bool = True) -> list:
        """Original proportional scaling for hybrid mode (unchanged behavior)."""
        num_clips = len(clips)
        crossfade_duration = 0.5
        crossfade_loss = (num_clips - 1) * crossfade_duration
        effective_duration = total_audio_duration + crossfade_loss
        total_needed = sum(c.get("duration_needed", 10) for c in clips)

        result = []
        for clip in clips:
            needed = clip.get("duration_needed", 10)

            if zoom:
                # Hybrid mode: proportional to audio, clamp images to 10s
                target_duration = (needed / total_needed) * total_audio_duration \
                    if total_needed > 0 else total_audio_duration / num_clips
                max_dur = 10.0 if clip.get("type") == "image" else 30.0
                target_duration = max(2.0, min(max_dur, target_duration))
            else:
                # Proportional to effective duration (compensate crossfades)
                target_duration = (needed / total_needed) * effective_duration \
                    if total_needed > 0 else effective_duration / num_clips
                target_duration = max(2.0, target_duration)

            result.append({**clip, "target_duration": target_duration})

        return result

    def _use_locked_timings(self, clips: list) -> list:
        """Use exact timestamps from audio-first segmentation.

        Compensates for crossfade overlap: each 0.5s crossfade consumes time
        from the end of the previous clip, so we extend clips slightly.
        """
        num_clips = len(clips)
        crossfade_duration = 0.5

        result = []
        for i, clip in enumerate(clips):
            start = clip.get("start_time", 0)
            end = clip.get("end_time", start + 5)
            base_duration = end - start

            # Add crossfade compensation: extend clip to account for overlap
            # Each clip (except last) loses ~0.5s to the next crossfade
            if i < num_clips - 1:
                target_duration = base_duration + crossfade_duration
            else:
                target_duration = base_duration

            target_duration = max(2.0, min(20.0, target_duration))
            result.append({**clip, "target_duration": target_duration})
        return result

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
