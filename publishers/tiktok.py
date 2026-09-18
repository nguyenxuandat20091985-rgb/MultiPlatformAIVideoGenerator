"""
TikTok Content Posting API publisher.

Supports Direct Post (FILE_UPLOAD) flow:
1. Initialize upload → receive publish_id + upload_url
2. Upload video binary in chunks
3. Poll status until PUBLISH_COMPLETE (or fail)

Requires a valid creator access_token with video.publish / video.upload scopes.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any, List, Optional

import requests

from config.settings import settings
from .base import BasePublisher, PublishResult

TIKTOK_API_BASE = "https://open.tiktokapis.com"


class TikTokPublisher(BasePublisher):
    name = "tiktok"

    def is_configured(self) -> bool:
        return bool(settings.TIKTOK_ACCESS_TOKEN)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {settings.TIKTOK_ACCESS_TOKEN}",
            "Content-Type": "application/json; charset=UTF-8",
        }

    def publish(
        self,
        video_path: Path,
        title: str,
        description: str = "",
        tags: Optional[List[str]] = None,
        privacy_level: Optional[str] = None,
        disable_duet: bool = False,
        disable_comment: bool = False,
        disable_stitch: bool = False,
        **kwargs: Any,
    ) -> PublishResult:
        if not self.is_configured():
            return PublishResult(
                platform=self.name,
                success=False,
                message="TIKTOK_ACCESS_TOKEN is not set.",
            )
        if not video_path.exists():
            return PublishResult(
                platform=self.name,
                success=False,
                message=f"Video file not found: {video_path}",
            )

        privacy = privacy_level or settings.TIKTOK_PRIVACY_LEVEL
        caption = title
        if description:
            caption = f"{title}\n\n{description}"
        if tags:
            hashtags = " ".join(f"#{t.lstrip('#')}" for t in tags)
            caption = f"{caption}\n{hashtags}"

        # TikTok caption limit ≈ 2200 chars
        caption = caption[:2200]

        file_size = video_path.stat().st_size
        # Prefer single chunk when file < 64 MB
        chunk_size = min(file_size, 64 * 1024 * 1024)
        total_chunks = max(1, (file_size + chunk_size - 1) // chunk_size)

        # ---- Step 1: Initialize Direct Post ----
        init_body = {
            "post_info": {
                "title": caption,
                "privacy_level": privacy,
                "disable_duet": disable_duet,
                "disable_comment": disable_comment,
                "disable_stitch": disable_stitch,
                "video_cover_timestamp_ms": 1000,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": file_size,
                "chunk_size": chunk_size,
                "total_chunk_count": total_chunks,
            },
        }

        try:
            init_resp = requests.post(
                f"{TIKTOK_API_BASE}/v2/post/publish/video/init/",
                headers=self._headers(),
                json=init_body,
                timeout=30,
            )
            init_data = init_resp.json()
            if init_resp.status_code != 200 or init_data.get("error", {}).get("code") not in (
                None,
                "ok",
                0,
            ):
                err = init_data.get("error") or init_data
                return PublishResult(
                    platform=self.name,
                    success=False,
                    message=f"Init failed: {err}",
                    raw=init_data,
                )

            data = init_data.get("data", {})
            publish_id = data.get("publish_id")
            upload_url = data.get("upload_url")
            if not publish_id or not upload_url:
                return PublishResult(
                    platform=self.name,
                    success=False,
                    message="Missing publish_id or upload_url in init response",
                    raw=init_data,
                )

            print(f"   TikTok init OK – publish_id={publish_id}")

            # ---- Step 2: Upload chunks ----
            with open(video_path, "rb") as f:
                for i in range(total_chunks):
                    start = i * chunk_size
                    end = min(start + chunk_size, file_size) - 1
                    chunk = f.read(end - start + 1)
                    headers = {
                        "Content-Type": "video/mp4",
                        "Content-Length": str(len(chunk)),
                        "Content-Range": f"bytes {start}-{end}/{file_size}",
                    }
                    up = requests.put(upload_url, headers=headers, data=chunk, timeout=120)
                    if up.status_code not in (200, 201, 206):
                        return PublishResult(
                            platform=self.name,
                            success=False,
                            message=f"Chunk upload failed ({up.status_code}): {up.text[:200]}",
                        )
                    print(f"   Uploaded chunk {i + 1}/{total_chunks}")

            # ---- Step 3: Poll status ----
            status = self._wait_for_publish(publish_id)
            if status.get("status") == "PUBLISH_COMPLETE":
                post_ids = status.get("publicaly_available_post_id") or status.get(
                    "publicly_available_post_id"
                )
                post_id = post_ids[0] if isinstance(post_ids, list) and post_ids else None
                return PublishResult(
                    platform=self.name,
                    success=True,
                    post_id=str(post_id) if post_id else publish_id,
                    message="Published successfully on TikTok",
                    raw=status,
                )
            return PublishResult(
                platform=self.name,
                success=False,
                message=f"Publish ended with status: {status.get('status')}",
                raw=status,
            )

        except Exception as e:
            return PublishResult(
                platform=self.name,
                success=False,
                message=str(e),
            )

    def _wait_for_publish(self, publish_id: str, max_attempts: int = 30, interval: float = 5.0) -> dict:
        for attempt in range(max_attempts):
            resp = requests.post(
                f"{TIKTOK_API_BASE}/v2/post/publish/status/fetch/",
                headers=self._headers(),
                json={"publish_id": publish_id},
                timeout=20,
            )
            data = resp.json().get("data", {})
            status = data.get("status", "")
            print(f"   TikTok status [{attempt + 1}]: {status}")
            if status in ("PUBLISH_COMPLETE", "FAILED", "PUBLISH_FAILED"):
                return data
            time.sleep(interval)
        return {"status": "TIMEOUT", "publish_id": publish_id}
