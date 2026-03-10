"""QA Agent — reviews quality, generates styled subtitles, packages final assets."""

import os
import structlog

from app.agents.base import BaseAgent

logger = structlog.get_logger(__name__)


class QAAgent(BaseAgent):
    agent_name = "qa_agent"
    phase_number = 6

    def run(self, input_data: dict, learning_context: list) -> dict:
        pipeline_run_id = input_data.get("pipeline_run_id", "")
        config = input_data.get("pipeline_config", {})

        # Gather outputs from all previous phases
        phase_2 = input_data.get("phase_2_output", {})
        phase_3 = input_data.get("phase_3_output", {})
        phase_4 = input_data.get("phase_4_output", {})
        phase_5 = input_data.get("phase_5_output", {})

        title = phase_2.get("selected_title", "")
        description = phase_2.get("description", "")
        script = phase_2.get("script", "")
        tags = phase_2.get("tags", [])
        video_id = phase_2.get("video_id")
        thumbnail = phase_3.get("thumbnail", {})
        audio_path = phase_4.get("audio_path", "")
        video_path = phase_5.get("video_path", "")

        language = input_data.get("language", "en")

        logger.info("qa.start", title=title, video_id=video_id, language=language)

        from app.utils.file_manager import get_video_dir
        video_dir = get_video_dir(pipeline_run_id)

        # Step 1: Generate subtitles from audio using Whisper (language-aware)
        subtitle_path = self._generate_subtitles(audio_path, video_dir, language=language)

        # Step 2: Review script quality via LLM
        review = self._review_script(script, title, input_data.get("niche", ""))

        # Step 3: Burn styled subtitles into video
        subtitled_video = self._burn_styled_subtitles(
            video_path, subtitle_path, video_dir
        )

        # Step 4: Update video record to "ready"
        self._finalize_video(video_id, subtitle_path, subtitled_video or video_path)

        # Step 5: Compile upload package
        upload_package = {
            "title": title,
            "description": description,
            "tags": tags,
            "video_file": subtitled_video or video_path,
            "video_file_no_subs": video_path,
            "thumbnail_file": thumbnail.get("local_path", "") if thumbnail else "",
            "subtitle_file": subtitle_path,
            "audio_file": audio_path,
        }

        # Step 6: Sync files to web service for downloads (Railway deployment)
        self._sync_to_web_service(pipeline_run_id, upload_package)

        result = {
            "video_id": video_id,
            "upload_package": upload_package,
            "qa_review": review,
            "subtitle_path": subtitle_path,
            "status": "ready_for_upload",
        }

        logger.info("qa.complete", title=title, status="ready_for_upload",
                     qa_score=review.get("score"))
        return result

    def _generate_subtitles(self, audio_path: str, video_dir: str, language: str = "en") -> str:
        """Generate SRT subtitles from narration audio using Whisper."""
        if not audio_path or not os.path.exists(audio_path):
            logger.warning("qa.no_audio_for_subtitles")
            return ""

        try:
            from app.integrations.whisper_client import transcribe

            srt_content = transcribe(audio_path, output_format="srt", language=language)

            subtitle_path = os.path.join(video_dir, "subtitles.srt")
            with open(subtitle_path, "w") as f:
                f.write(srt_content)

            logger.info("qa.subtitles_generated", path=subtitle_path)
            return subtitle_path
        except Exception as e:
            logger.error("qa.subtitle_generation_failed", error=str(e))
            return ""

    def _review_script(self, script: str, title: str, niche: str) -> dict:
        """Use LLM to review script quality."""
        try:
            prompt = self.get_prompt(
                "review_script",
                script=script[:3000],
                title=title,
                niche=niche,
            )

            result = self.call_llm("openai", prompt, json_mode=True)
            parsed = self.parse_json_response(result) if isinstance(result, str) else result

            return parsed
        except Exception as e:
            logger.warning("qa.review_failed", error=str(e))
            return {"score": 0, "issues": [], "suggestions": [], "approved": True}

    def _burn_styled_subtitles(self, video_path: str, subtitle_path: str,
                                video_dir: str) -> str:
        """Burn professionally styled subtitles into the video."""
        if not video_path or not subtitle_path:
            return ""
        if not os.path.exists(video_path) or not os.path.exists(subtitle_path):
            return ""

        try:
            from app.integrations.ffmpeg_client import add_subtitles_styled

            output_path = os.path.join(video_dir, "final_video_subtitled.mp4")
            return add_subtitles_styled(
                video_path, subtitle_path, output_path,
                font="Sans",
                fontsize=20,
                style="minimal",
            )
        except Exception as e:
            logger.warning("qa.burn_subtitles_failed", error=str(e))
            return ""

    def _finalize_video(self, video_id: str, subtitle_path: str,
                        final_video_path: str):
        """Mark the video as ready for upload."""
        if not video_id:
            return
        try:
            from app import db
            from app.models.video import Video

            video = Video.query.get(video_id)
            if video:
                video.status = "ready"
                video.subtitle_path = subtitle_path
                video.final_video_path = final_video_path
                db.session.commit()
                logger.info("qa.video_finalized", video_id=video_id)
        except Exception as e:
            logger.warning("qa.finalize_failed", error=str(e))

    def _sync_to_web_service(self, pipeline_id: str, upload_package: dict):
        """Upload final files to web service volume for download access.

        In Railway deployment, worker and web have separate filesystems.
        This syncs files from worker volume to web volume via internal HTTP.
        """
        import httpx

        # Railway internal networking: web.railway.internal
        web_url = os.environ.get("WEB_INTERNAL_URL", "http://web.railway.internal:5000")
        upload_endpoint = f"{web_url}/api/internal/upload/{pipeline_id}"

        files_to_sync = [
            ("video", upload_package.get("video_file")),
            ("audio", upload_package.get("audio_file")),
            ("subtitle", upload_package.get("subtitle_file")),
            ("thumbnail", upload_package.get("thumbnail_file")),
        ]

        synced = 0
        for file_type, file_path in files_to_sync:
            if not file_path or not os.path.exists(file_path):
                continue

            try:
                with open(file_path, "rb") as f:
                    response = httpx.post(
                        f"{upload_endpoint}/{file_type}",
                        files={"file": (os.path.basename(file_path), f)},
                        timeout=300,  # 5 min for large videos
                    )
                    if response.status_code == 200:
                        synced += 1
                        logger.info("qa.sync_file_ok", file_type=file_type,
                                    size=os.path.getsize(file_path))
                    else:
                        logger.warning("qa.sync_file_failed", file_type=file_type,
                                       status=response.status_code)
            except Exception as e:
                # Don't fail the pipeline if sync fails - files still exist on worker volume
                logger.warning("qa.sync_error", file_type=file_type, error=str(e))

        logger.info("qa.sync_complete", pipeline_id=pipeline_id, files_synced=synced)
