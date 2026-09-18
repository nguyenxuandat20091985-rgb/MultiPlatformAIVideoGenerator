"""
Facebook Graph API – publish Reels to a Page.

Flow (official Reels Publishing API):
1. POST /{page-id}/video_reels  upload_phase=start  → video_id + upload_url
2. POST binary to rupload.facebook.com/video-upload/{video_id}
3. POST /{page-id}/video_reels  upload_phase=finish  → publish
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, List, Optional

import requests

from config.settings import settings
from .base import BasePublisher, PublishResult


class FacebookPublisher(BasePublisher):
    name = "facebook"

    def is_configured(self) -> bool:
        return bool(settings.FACEBOOK_PAGE_ID and settings.FACEBOOK_PAGE_ACCESS_TOKEN)

    @property
    def _graph(self) -> str:
        return f"https://graph.facebook.com/{settings.FACEBOOK_API_VERSION}"

    def publish(
        self,
        video_path: Path,
        title: str,
        description: str = "",
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> PublishResult:
        if not self.is_configured():
            return PublishResult(
                platform=self.name,
                success=False,
                message="FACEBOOK_PAGE_ID or FACEBOOK_PAGE_ACCESS_TOKEN missing.",
            )
        if not video_path.exists():
            return PublishResult(
                platform=self.name,
                success=False,
                message=f"Video file not found: {video_path}",
            )

        page_id = settings.FACEBOOK_PAGE_ID
        token = settings.FACEBOOK_PAGE_ACCESS_TOKEN
        caption = title
        if description:
            caption = f"{title}\n\n{description}"
        if tags:
            caption += "\n" + " ".join(f"#{t.lstrip('#')}" for t in tags)

        try:
            # ---- 1. Start upload session ----
            start_resp = requests.post(
                f"{self._graph}/{page_id}/video_reels",
                data={
                    "upload_phase": "start",
                    "access_token": token,
                },
                timeout=30,
            )
            start_data = start_resp.json()
            if "video_id" not in start_data:
                return PublishResult(
                    platform=self.name,
                    success=False,
                    message=f"Start phase failed: {start_data}",
                    raw=start_data,
                )
            video_id = start_data["video_id"]
            print(f"   Facebook upload session started – video_id={video_id}")

            # ---- 2. Upload binary to rupload ----
            file_size = video_path.stat().st_size
            with open(video_path, "rb") as f:
                binary = f.read()

            upload_headers = {
                "Authorization": f"OAuth {token}",
                "offset": "0",
                "file_size": str(file_size),
                "Content-Type": "application/octet-stream",
            }
            up_resp = requests.post(
                f"https://rupload.facebook.com/video-upload/{settings.FACEBOOK_API_VERSION}/{video_id}",
                headers=upload_headers,
                data=binary,
                timeout=300,
            )
            if up_resp.status_code not in (200, 201):
                return PublishResult(
                    platform=self.name,
                    success=False,
                    message=f"Binary upload failed ({up_resp.status_code}): {up_resp.text[:300]}",
                )
            print("   Facebook binary upload OK")

            # ---- 3. Finish / publish ----
            finish_resp = requests.post(
                f"{self._graph}/{page_id}/video_reels",
                data={
                    "upload_phase": "finish",
                    "video_id": video_id,
                    "title": title[:255],
                    "description": caption[:5000],
                    "access_token": token,
                    "video_state": "PUBLISHED",
                },
                timeout=60,
            )
            finish_data = finish_resp.json()
            success = finish_data.get("success") is True or "id" in finish_data or "post_id" in finish_data
            post_id = (
                finish_data.get("post_id")
                or finish_data.get("id")
                or video_id
            )
            if success:
                return PublishResult(
                    platform=self.name,
                    success=True,
                    post_id=str(post_id),
                    message=f"Reel published on Facebook Page (id={post_id})",
                    raw=finish_data,
                )
            return PublishResult(
                platform=self.name,
                success=False,
                message=f"Finish phase failed: {finish_data}",
                raw=finish_data,
            )

        except Exception as e:
            return PublishResult(
                platform=self.name,
                success=False,
                message=str(e),
            )
