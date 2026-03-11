"""Media Agent — collects stock footage per scene and generates thumbnails."""

import os
import structlog

from app.agents.base import BaseAgent

logger = structlog.get_logger(__name__)

STYLE_MAP = {
    "cinematic": "Photorealistic photograph, shot on 35mm film. Natural muted color palette with occasional warm lamplight accents. Shallow depth of field, slight film grain. Looks like a still frame from an independent drama film. Realistic imperfect lighting — mixed daylight from windows and warm incandescent bulbs. Natural skin textures, no airbrushing. Grounded, documentary-style realism.",
    "anime": "Japanese anime art style, vibrant cel-shaded colors, clean linework, expressive characters, Studio Ghibli influenced, warm color palette, detailed interior backgrounds, dramatic emotional compositions.",
    "watercolor": "Soft watercolor painting style, flowing washes of color, visible brush strokes, dreamy atmosphere, paper texture, warm muted tones, character-focused intimate composition.",
    "comic": "Bold comic book illustration, thick ink outlines, halftone dots, dynamic composition, vibrant flat colors, panel-style framing, expressive character faces, dramatic angles.",
    "gothic": "Dark gothic aesthetic, deep shadows, moody atmosphere, desaturated colors with crimson accents, dramatic chiaroscuro lighting, candlelit interiors, intimate character framing, baroque composition.",
    "minimalist": "Clean minimalist design, flat vector colors, simple geometric shapes, solid backgrounds, modern graphic design aesthetic, character silhouettes and simple scenes, bold negative space.",
    "retro": "Retro 1970s aesthetic, warm faded color palette, film grain, vintage photography feel, muted oranges and teals, nostalgic indoor lighting, character-driven composition, Kodachrome colors.",
    "fantasy": "Ethereal fantasy art, magical glowing elements, otherworldly landscapes, rich saturated colors, detailed digital painting style, expressive characters in enchanted settings, bioluminescent accents.",
}


class MediaAgent(BaseAgent):
    agent_name = "media_agent"
    phase_number = 4

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

        pipeline_run_id = input_data.get("pipeline_run_id", "")

        mode = config.get("mode", "hybrid")
        style_key = config.get("style", "cinematic")
        max_scenes = config.get("max_scenes")  # For testing: limit number of scenes

        logger.info("media.start", title=title, sections=len(sections), mode=mode, max_scenes=max_scenes)

        if mode == "story":
            # Story mode: all AI-generated images, no stock video
            scenes = self._extract_scenes_story(sections, style_key)
            if max_scenes and len(scenes) > max_scenes:
                logger.info("media.scenes_limited", original=len(scenes), limited=max_scenes)
                scenes = scenes[:max_scenes]
            scene_clips = self._generate_story_images(scenes, pipeline_run_id, video_id, style_key)
        else:
            # Hybrid mode: mix of stock video + AI images (existing logic)
            scenes = self._extract_scenes(sections)
            if max_scenes and len(scenes) > max_scenes:
                logger.info("media.scenes_limited", original=len(scenes), limited=max_scenes)
                scenes = scenes[:max_scenes]

            stock_scenes = [s for s in scenes if s.get("media_type") != "ai_image"]
            ai_scenes = [s for s in scenes if s.get("media_type") == "ai_image"]

            logger.info("media.scene_split", stock=len(stock_scenes), ai=len(ai_scenes))

            stock_clips = self._fetch_stock_clips(stock_scenes, pipeline_run_id, video_id) if stock_scenes else []
            ai_clips = self._generate_scene_images(ai_scenes, pipeline_run_id, video_id) if ai_scenes else []

            scene_clips = sorted(stock_clips + ai_clips, key=lambda x: x.get("scene_number", 0))

        # Step 3: Generate thumbnail
        thumbnail = self._generate_thumbnail(niche, title, pipeline_run_id)

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
                "media_type": "stock_video",
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

    def _generate_scene_images(self, scenes: list, pipeline_run_id: str, video_id: str = None) -> list:
        """Generate AI images for scenes tagged as ai_image, with stock fallback."""
        from app.integrations.ideogram_client import generate_image_v3, generate_image
        from app.utils.file_manager import get_video_dir
        import httpx

        video_dir = get_video_dir(pipeline_run_id)
        images_dir = os.path.join(video_dir, "ai_images")
        os.makedirs(images_dir, exist_ok=True)

        negative_prompt = "text, words, letters, watermark, blurry, low quality, logos, amateur, grainy, distorted, deformed"
        scene_clips = []

        for scene in scenes:
            scene_num = scene.get("scene_number", 0)
            prompt = scene.get("image_prompt", scene.get("visual_description", ""))

            try:
                # Try V3 first, fallback to V2
                try:
                    result = generate_image_v3(
                        prompt=prompt,
                        aspect_ratio="16x9",
                        style_type="GENERAL",
                        negative_prompt=negative_prompt,
                    )
                except Exception:
                    logger.info("media.scene_image_v3_failed_trying_v2", scene=scene_num)
                    result = generate_image(
                        prompt=prompt,
                        aspect_ratio="16:9",
                        style="GENERAL",
                        negative_prompt=negative_prompt,
                    )

                if result.get("url"):
                    image_path = os.path.join(images_dir, f"scene_{scene_num:03d}.png")
                    response = httpx.get(result["url"], timeout=60, follow_redirects=True)
                    with open(image_path, "wb") as f:
                        f.write(response.content)

                    scene_clips.append({
                        "scene_number": scene_num,
                        "section_name": scene.get("section_name"),
                        "media_type": "ai_image",
                        "clips": [{"type": "image", "local_path": image_path, "source": "ideogram"}],
                        "duration_needed": scene.get("duration_seconds", 30),
                    })
                    logger.info("media.scene_image_generated", scene=scene_num)
                else:
                    raise ValueError("Ideogram returned no URL")

            except Exception as e:
                logger.warning("media.scene_image_failed_fallback_stock",
                             scene=scene_num, error=str(e))
                # Fallback: treat as stock_video scene
                fallback = self._fetch_stock_clips([scene], pipeline_run_id, video_id)
                for entry in fallback:
                    entry["media_type"] = "stock_video"
                scene_clips.extend(fallback)

        # Save AI image assets
        self._save_image_assets(scene_clips, pipeline_run_id, video_id)

        return scene_clips

    def _extract_scenes_story(self, sections: list, style_key: str) -> list:
        """Use LLM to break script into all-AI-image scenes for story mode."""
        sections_str = ""
        for i, s in enumerate(sections):
            sections_str += f"Section {i+1}: {s.get('name', 'Unnamed')}\n"
            sections_str += f"Text: {s.get('text', '')}\n"
            sections_str += f"Duration: {s.get('duration_estimate', 60)}s\n\n"

        style_description = STYLE_MAP.get(style_key, STYLE_MAP["cinematic"])
        prompt = self.get_prompt(
            "extract_scenes_story",
            sections=sections_str,
            style_description=style_description,
        )

        result = self.call_llm("anthropic", prompt, json_mode=True, max_tokens=32768)
        parsed = self.parse_json_response(result) if isinstance(result, str) else result

        scenes = parsed.get("scenes", [])
        # Force all scenes to ai_image
        for s in scenes:
            s["media_type"] = "ai_image"

        # Cap scenes at 70 max — LLM sometimes overshoots
        if len(scenes) > 70:
            logger.warning("media.scenes_capped", original=len(scenes), capped=70)
            scenes = scenes[:70]

        logger.info("media.story_scenes_extracted", count=len(scenes), style=style_key)
        return scenes

    def _generate_story_images(self, scenes: list, pipeline_run_id: str,
                               video_id: str = None, style_key: str = "cinematic") -> list:
        """Generate all scene images using GPT Image 1 for story mode.
        Handles reuse_scene references — copies image path instead of regenerating."""
        from app.integrations.openai_client import generate_image
        from app.utils.file_manager import get_video_dir

        video_dir = get_video_dir(pipeline_run_id)
        images_dir = os.path.join(video_dir, "ai_images")
        os.makedirs(images_dir, exist_ok=True)

        style_prefix = STYLE_MAP.get(style_key, STYLE_MAP["cinematic"])
        scene_clips = []
        # Track image paths by scene_number for reuse lookups
        image_paths = {}

        # First pass: generate images for original scenes (no reuse_scene)
        for scene in scenes:
            if scene.get("reuse_scene"):
                continue  # Handle in second pass

            scene_num = scene.get("scene_number", 0)
            raw_prompt = scene.get("image_prompt", scene.get("visual_description", ""))
            full_prompt = f"{style_prefix} {raw_prompt}"

            image_path = os.path.join(images_dir, f"scene_{scene_num:03d}.png")

            try:
                # Primary: GPT Image 1
                image_bytes = generate_image(prompt=full_prompt, quality="high")
                with open(image_path, "wb") as f:
                    f.write(image_bytes)
                logger.info("media.story_image_generated", scene=scene_num, source="gpt-image-1")

            except Exception as e:
                logger.warning("media.story_gpt_failed_trying_ideogram",
                             scene=scene_num, error=str(e))
                # Fallback: Ideogram
                try:
                    from app.integrations.ideogram_client import generate_image_v3, generate_image as ideogram_gen
                    import httpx

                    neg = "text, words, letters, watermark, blurry, low quality, logos"
                    try:
                        result = generate_image_v3(
                            prompt=full_prompt, aspect_ratio="16x9",
                            style_type="GENERAL", negative_prompt=neg,
                        )
                    except Exception:
                        result = ideogram_gen(
                            prompt=full_prompt, aspect_ratio="16:9",
                            style="GENERAL", negative_prompt=neg,
                        )

                    if result.get("url"):
                        resp = httpx.get(result["url"], timeout=60, follow_redirects=True)
                        with open(image_path, "wb") as f:
                            f.write(resp.content)
                        logger.info("media.story_image_generated", scene=scene_num, source="ideogram")
                    else:
                        raise ValueError("Ideogram returned no URL")

                except Exception as e2:
                    logger.error("media.story_image_all_failed",
                               scene=scene_num, error=str(e2))
                    continue

            image_paths[scene_num] = image_path
            scene_clips.append({
                "scene_number": scene_num,
                "section_name": scene.get("section_name"),
                "media_type": "ai_image",
                "clips": [{"type": "image", "local_path": image_path, "source": "gpt-image-1"}],
                "duration_needed": scene.get("duration_seconds", 12),
                "effect": scene.get("effect", "slow_zoom_in"),
                "narration_text": scene.get("narration_text", ""),
            })

        # Second pass: handle reuse_scene references (copy image path, skip generation)
        for scene in scenes:
            if not scene.get("reuse_scene"):
                continue

            scene_num = scene.get("scene_number", 0)
            original_num = scene["reuse_scene"]
            original_path = image_paths.get(original_num)

            if original_path and os.path.exists(original_path):
                scene_clips.append({
                    "scene_number": scene_num,
                    "section_name": scene.get("section_name"),
                    "media_type": "ai_image",
                    "clips": [{"type": "image", "local_path": original_path, "source": "reuse"}],
                    "duration_needed": scene.get("duration_seconds", 12),
                    "effect": scene.get("effect", "slow_zoom_in"),
                    "narration_text": scene.get("narration_text", ""),
                })
                logger.info("media.story_image_reused", scene=scene_num, original=original_num)
            else:
                logger.warning("media.story_reuse_missing", scene=scene_num,
                             original=original_num)

        # Sort by scene_number to maintain correct order
        scene_clips.sort(key=lambda x: x.get("scene_number", 0))

        # Save asset records
        self._save_image_assets(scene_clips, pipeline_run_id, video_id)

        reuse_count = sum(1 for s in scenes if s.get("reuse_scene"))
        logger.info("media.story_images_complete",
                    total=len(scenes), generated=len(scenes) - reuse_count,
                    reused=reuse_count, clips=len(scene_clips))
        return scene_clips

    def _save_image_assets(self, scene_clips: list, pipeline_run_id: str, video_id: str = None):
        """Save AI image references as Asset records."""
        try:
            from app import db
            from app.models.asset import Asset

            for sc in scene_clips:
                if sc.get("media_type") != "ai_image":
                    continue
                for clip in sc.get("clips", []):
                    asset = Asset(
                        video_id=video_id,
                        type="scene_image",
                        url=clip.get("local_path", ""),
                        metadata_json={
                            "source": "ideogram",
                            "scene_number": sc.get("scene_number"),
                            "media_type": "ai_image",
                        },
                    )
                    db.session.add(asset)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.warning("media.save_image_assets_failed", error=str(e))

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
