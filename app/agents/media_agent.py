"""Media Agent — collects stock footage per scene and generates thumbnails."""

import os
import structlog

from app.agents.base import BaseAgent

logger = structlog.get_logger(__name__)


class MediaAgent(BaseAgent):
    agent_name = "media_agent"
    phase_number = 3

    def run(self, input_data: dict, learning_context: list) -> dict:
        niche = input_data.get("niche", "")
        config = input_data.get("pipeline_config", {})

        # Get script data from Phase 2
        phase_2 = input_data.get("phase_2_output", {})
        script = phase_2.get("script", "")
        sections = phase_2.get("sections", [])
        title = phase_2.get("selected_title", "")
        video_id = phase_2.get("video_id")

        if not script:
            raise ValueError("No script from Phase 2 — cannot collect media")

        logger.info("media.start", title=title, sections=len(sections))

        # Step 1: Use LLM to break script into visual scenes with search keywords
        scenes = self._extract_scenes(sections)

        # Step 2: Search stock footage for each scene
        scene_clips = self._fetch_stock_clips(scenes, input_data.get("pipeline_run_id", ""), video_id)

        # Step 3: Generate thumbnail
        thumbnail = self._generate_thumbnail(niche, title, input_data.get("pipeline_run_id", ""))

        result = {
            "video_id": video_id,
            "scenes": scenes,
            "scene_clips": scene_clips,
            "thumbnail": thumbnail,
            "total_scenes": len(scenes),
            "clips_found": sum(1 for sc in scene_clips if sc.get("clips")),
        }

        logger.info("media.complete", scenes=len(scenes), clips_found=result["clips_found"])
        return result

    def _extract_scenes(self, sections: list) -> list:
        """Use LLM to break script sections into visual scenes."""
        sections_str = ""
        for i, s in enumerate(sections):
            sections_str += f"Section {i+1}: {s.get('name', 'Unnamed')}\n"
            sections_str += f"Text: {s.get('text', '')[:500]}\n"
            sections_str += f"Duration: {s.get('duration_estimate', 60)}s\n\n"

        prompt = self.get_prompt("extract_scenes", sections=sections_str)

        result = self.call_llm("anthropic", prompt, json_mode=True)
        parsed = self.parse_json_response(result) if isinstance(result, str) else result

        return parsed.get("scenes", [])

    def _fetch_stock_clips(self, scenes: list, pipeline_run_id: str, video_id: str = None) -> list:
        """Search Pexels and Pixabay for stock clips matching each scene."""
        scene_clips = []

        for scene in scenes:
            keywords = scene.get("search_keywords", [])
            query = " ".join(keywords[:3]) if keywords else scene.get("visual_description", "")[:50]

            clips = []

            # Try Pexels first
            try:
                from app.integrations.pexels_client import search_videos as pexels_search
                pexels_results = pexels_search(query, orientation="landscape", per_page=3)
                for v in pexels_results:
                    # Pick the best quality video file
                    video_files = v.get("video_files", [])
                    best_file = next((f for f in video_files if f.get("quality") == "hd"), video_files[0] if video_files else None)
                    if best_file:
                        clips.append({
                            "source": "pexels",
                            "url": best_file["link"],
                            "quality": best_file.get("quality"),
                            "duration": v.get("duration"),
                            "preview": v.get("video_pictures", [None])[0] if v.get("video_pictures") else None,
                        })
            except Exception as e:
                logger.warning("media.pexels_failed", query=query, error=str(e))

            # Fallback to Pixabay if not enough clips
            if len(clips) < 2:
                try:
                    from app.integrations.pixabay_client import search_videos as pixabay_search
                    pixabay_results = pixabay_search(query, per_page=3)
                    for v in pixabay_results:
                        videos = v.get("videos", {})
                        large = videos.get("large", {})
                        if large.get("url"):
                            clips.append({
                                "source": "pixabay",
                                "url": large["url"],
                                "quality": "large",
                                "duration": v.get("duration"),
                            })
                except Exception as e:
                    logger.warning("media.pixabay_failed", query=query, error=str(e))

            scene_clips.append({
                "scene_number": scene.get("scene_number"),
                "section_name": scene.get("section_name"),
                "query": query,
                "clips": clips,
                "duration_needed": scene.get("duration_seconds", 30),
            })

        # Save clips as assets
        self._save_clip_assets(scene_clips, pipeline_run_id, video_id)

        return scene_clips

    def _generate_thumbnail(self, niche: str, title: str, pipeline_run_id: str) -> dict:
        """Generate a thumbnail image using Ideogram."""
        # First, get a thumbnail prompt from LLM
        prompt = self.get_prompt("thumbnail_prompt", title=title, niche=niche)
        result = self.call_llm("openai", prompt, json_mode=True)
        parsed = self.parse_json_response(result) if isinstance(result, str) else result

        image_prompt = parsed.get("prompt", f"Eye-catching YouTube thumbnail for {title}")
        negative_prompt = parsed.get("negative_prompt", "text, words, letters, watermark, blurry, low quality")

        # Generate with Ideogram (try V3, fallback to V2)
        try:
            from app.integrations.ideogram_client import generate_image_v3, generate_image

            try:
                thumbnail = generate_image_v3(
                    prompt=image_prompt,
                    aspect_ratio="16x9",
                    style_type="DESIGN",
                    negative_prompt=negative_prompt,
                )
            except Exception:
                logger.info("media.thumbnail_v3_failed_trying_v2")
                thumbnail = generate_image(
                    prompt=image_prompt,
                    aspect_ratio="16:9",
                    style="DESIGN",
                    negative_prompt=negative_prompt,
                )

            # Download and save the thumbnail
            if thumbnail.get("url"):
                from app.utils.file_manager import get_video_dir
                video_dir = get_video_dir(pipeline_run_id)
                thumb_path = os.path.join(video_dir, "thumbnail.png")

                import httpx
                response = httpx.get(thumbnail["url"], timeout=60, follow_redirects=True)
                with open(thumb_path, "wb") as f:
                    f.write(response.content)

                thumbnail["local_path"] = thumb_path

            return thumbnail
        except Exception as e:
            logger.error("media.thumbnail_failed", error=str(e))
            return {"error": str(e), "prompt": image_prompt}

    def _save_clip_assets(self, scene_clips: list, pipeline_run_id: str, video_id: str = None):
        """Save clip references as Asset records."""
        try:
            from app import db
            from app.models.asset import Asset

            for sc in scene_clips:
                for clip in sc.get("clips", []):
                    asset = Asset(
                        video_id=video_id,
                        type="stock_clip",
                        url=clip.get("url"),
                        metadata_json={
                            "source": clip.get("source"),
                            "scene_number": sc.get("scene_number"),
                            "query": sc.get("query"),
                            "quality": clip.get("quality"),
                            "duration": clip.get("duration"),
                        },
                    )
                    db.session.add(asset)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.warning("media.save_assets_failed", error=str(e))
