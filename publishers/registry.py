"""
Publisher registry – central place to discover and invoke platform publishers.

Adding a new network later only requires:
1. Implement a class inheriting BasePublisher
2. Register it in PUBLISHERS dict below
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Type

from .base import BasePublisher, PublishResult
from .youtube import YouTubePublisher
from .tiktok import TikTokPublisher
from .facebook import FacebookPublisher

# Extensible registry – add new platforms here
PUBLISHERS: Dict[str, Type[BasePublisher]] = {
    "youtube": YouTubePublisher,
    "tiktok": TikTokPublisher,
    "facebook": FacebookPublisher,
    # Future examples:
    # "instagram": InstagramPublisher,
    # "linkedin": LinkedInPublisher,
    # "x": XPublisher,
}


def get_publisher(name: str) -> BasePublisher:
    key = name.lower().strip()
    if key not in PUBLISHERS:
        raise ValueError(
            f"Unknown platform '{name}'. Available: {', '.join(PUBLISHERS)}"
        )
    return PUBLISHERS[key]()


def list_available_publishers(configured_only: bool = False) -> List[str]:
    names = []
    for name, cls in PUBLISHERS.items():
        pub = cls()
        if not configured_only or pub.is_configured():
            names.append(name)
    return names


def publish_to_platforms(
    video_path: Path,
    title: str,
    description: str = "",
    tags: Optional[List[str]] = None,
    platforms: Optional[List[str]] = None,
) -> List[PublishResult]:
    """
    Publish the same video to one or more platforms.
    If platforms is None, publish to every currently configured platform.
    """
    if platforms is None:
        platforms = list_available_publishers(configured_only=True)

    results: List[PublishResult] = []
    for name in platforms:
        try:
            publisher = get_publisher(name)
            if not publisher.is_configured():
                results.append(
                    PublishResult(
                        platform=name,
                        success=False,
                        message="Not configured (missing credentials)",
                    )
                )
                continue
            print(f"\n📤 Publishing to {name.upper()}...")
            result = publisher.publish(
                video_path=video_path,
                title=title,
                description=description,
                tags=tags,
            )
            results.append(result)
            print(result)
        except Exception as e:
            results.append(
                PublishResult(platform=name, success=False, message=str(e))
            )
    return results
