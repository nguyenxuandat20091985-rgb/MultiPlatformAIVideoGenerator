#!/usr/bin/env python3
"""
MultiPlatformAIVideoGenerator
End-to-end pipeline: AI video generation → multi-platform auto-publishing.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from config.settings import settings
from core import (
    generate_script,
    save_script,
    generate_image_prompts,
    generate_images,
    generate_audio,
    generate_captions,
    compose_video,
    add_captions_to_video,
)
from publishers import (
    list_available_publishers,
    publish_to_platforms,
)


BANNER = r"""
╔══════════════════════════════════════════════════════════════════╗
║          MultiPlatform AI Video Generator & Publisher            ║
║   TikTok · YouTube Shorts · Facebook Reels · Extensible          ║
╚══════════════════════════════════════════════════════════════════╝
"""


def create_project_folder(name: str) -> Path:
    base = settings.OUTPUT_DIR / name
    base.mkdir(parents=True, exist_ok=True)
    (base / "images").mkdir(exist_ok=True)
    (base / "audio").mkdir(exist_ok=True)
    (base / "captions").mkdir(exist_ok=True)
    return base


def run_generation(
    folder_name: str,
    topic: str,
    style: str,
    target_audience: str,
    cta: str,
    skip_captions: bool = False,
) -> Path:
    """Full generation pipeline. Returns path to final video."""
    settings.validate_generation()

    project = create_project_folder(folder_name)
    print(f"✅ Project folder: {project}")

    script_path = project / "script.json"
    prompts_path = project / "image_prompts.json"
    images_dir = project / "images"
    audio_dir = project / "audio"
    captions_dir = project / "captions"
    video_path = project / "final_video.mp4"
    final_path = project / "final_video_with_captions.mp4"

    print("\n🚀 [1/6] Generating script...")
    script_data = generate_script(topic, style, target_audience, cta)
    save_script(script_data, script_path)

    print("\n🎨 [2/6] Generating image prompts...")
    generate_image_prompts(script_path, prompts_path)

    print("\n🌄 [3/6] Generating images (FLUX)...")
    generate_images(prompts_path, images_dir)

    print("\n🔊 [4/6] Generating audio (TTS)...")
    audio_path = generate_audio(script_path, audio_dir)

    print("\n🎥 [5/6] Composing video...")
    compose_video(images_dir, audio_path, video_path)

    if skip_captions:
        print("\n⏭️  Skipping captions.")
        return video_path

    print("\n🔍 [6/6] Generating & burning captions...")
    captions_path = generate_captions(audio_path, captions_dir)
    add_captions_to_video(video_path, captions_path, final_path)

    print(f"\n📝 Duration ≈ {script_data.get('total_duration')}s")
    print(f"🎬 Scenes: {len(script_data.get('scenes', []))}")
    print(f"🖼️  Images: {len(list(images_dir.glob('*.jpeg')))}")
    print(f"🎥 Final video: {final_path}")
    return final_path


def run_publish(
    video_path: Path,
    title: str,
    description: str = "",
    tags: list | None = None,
    platforms: list | None = None,
) -> None:
    if not video_path.exists():
        print(f"❌ Video not found: {video_path}")
        sys.exit(1)

    available = list_available_publishers(configured_only=True)
    if not available:
        print(
            "⚠️  No platforms are configured. "
            "Set credentials in .env (see .env.example) and try again."
        )
        print(f"   Detected platforms (all): {list_available_publishers()}")
        return

    print(f"📡 Configured platforms: {', '.join(available)}")
    results = publish_to_platforms(
        video_path=video_path,
        title=title,
        description=description,
        tags=tags,
        platforms=platforms or available,
    )
    print("\n—— Publish summary ——")
    for r in results:
        print(r)


def interactive_mode() -> None:
    print(BANNER)
    folder = input("Project folder name: ").strip() or "my_video"
    topic = input("Video topic: ").strip()
    if not topic:
        print("❌ Topic is required.")
        return
    style = input(f"Style [{settings.DEFAULT_VIDEO_STYLE}]: ").strip() or settings.DEFAULT_VIDEO_STYLE
    audience = input(f"Target audience [{settings.DEFAULT_TARGET_AUDIENCE}]: ").strip() or settings.DEFAULT_TARGET_AUDIENCE
    cta = input(f"Call-to-action [{settings.DEFAULT_CTA}]: ").strip() or settings.DEFAULT_CTA

    final_video = run_generation(folder, topic, style, audience, cta)

    do_publish = input("\nPublish to social platforms now? [y/N]: ").strip().lower()
    if do_publish == "y":
        title = input(f"Post title [{topic}]: ").strip() or topic
        desc = input("Description (optional): ").strip()
        tags_raw = input("Tags (comma-separated, optional): ").strip()
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else None
        run_publish(final_video, title=title, description=desc, tags=tags)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AI Video Generator + Multi-Platform Auto Publisher"
    )
    sub = parser.add_subparsers(dest="command")

    # generate
    gen = sub.add_parser("generate", help="Generate a video only")
    gen.add_argument("--folder", required=True, help="Project folder name under output/")
    gen.add_argument("--topic", required=True)
    gen.add_argument("--style", default=None)
    gen.add_argument("--audience", default=None)
    gen.add_argument("--cta", default=None)
    gen.add_argument("--skip-captions", action="store_true")

    # publish
    pub = sub.add_parser("publish", help="Publish an existing video")
    pub.add_argument("--video", required=True, type=Path)
    pub.add_argument("--title", required=True)
    pub.add_argument("--description", default="")
    pub.add_argument("--tags", default="", help="Comma-separated tags")
    pub.add_argument(
        "--platforms",
        default="",
        help="Comma-separated: youtube,tiktok,facebook (default = all configured)",
    )

    # full pipeline
    full = sub.add_parser("run", help="Generate + optionally publish")
    full.add_argument("--folder", required=True)
    full.add_argument("--topic", required=True)
    full.add_argument("--style", default=None)
    full.add_argument("--audience", default=None)
    full.add_argument("--cta", default=None)
    full.add_argument("--title", default=None, help="Override post title (default = topic)")
    full.add_argument("--description", default="")
    full.add_argument("--tags", default="")
    full.add_argument("--platforms", default="")
    full.add_argument("--skip-captions", action="store_true")
    full.add_argument("--no-publish", action="store_true")

    # status
    sub.add_parser("status", help="Show which platforms are configured")

    args = parser.parse_args()

    if args.command is None:
        interactive_mode()
        return

    if args.command == "status":
        print("Configured platforms:")
        for name in list_available_publishers(configured_only=True):
            print(f"  ✅ {name}")
        print("\nAll registered platforms:")
        for name in list_available_publishers(configured_only=False):
            print(f"  • {name}")
        return

    if args.command == "generate":
        run_generation(
            folder_name=args.folder,
            topic=args.topic,
            style=args.style or settings.DEFAULT_VIDEO_STYLE,
            target_audience=args.audience or settings.DEFAULT_TARGET_AUDIENCE,
            cta=args.cta or settings.DEFAULT_CTA,
            skip_captions=args.skip_captions,
        )
        return

    if args.command == "publish":
        tags = [t.strip() for t in args.tags.split(",") if t.strip()] or None
        platforms = [p.strip() for p in args.platforms.split(",") if p.strip()] or None
        run_publish(
            video_path=args.video,
            title=args.title,
            description=args.description,
            tags=tags,
            platforms=platforms,
        )
        return

    if args.command == "run":
        final = run_generation(
            folder_name=args.folder,
            topic=args.topic,
            style=args.style or settings.DEFAULT_VIDEO_STYLE,
            target_audience=args.audience or settings.DEFAULT_TARGET_AUDIENCE,
            cta=args.cta or settings.DEFAULT_CTA,
            skip_captions=args.skip_captions,
        )
        if not args.no_publish:
            tags = [t.strip() for t in args.tags.split(",") if t.strip()] or None
            platforms = [p.strip() for p in args.platforms.split(",") if p.strip()] or None
            run_publish(
                video_path=final,
                title=args.title or args.topic,
                description=args.description,
                tags=tags,
                platforms=platforms,
            )


if __name__ == "__main__":
    main()
