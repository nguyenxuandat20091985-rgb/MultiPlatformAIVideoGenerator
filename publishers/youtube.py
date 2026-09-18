"""YouTube Data API v3 – upload Shorts / regular videos."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from config.settings import settings
from .base import BasePublisher, PublishResult

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


class YouTubePublisher(BasePublisher):
    name = "youtube"

    def __init__(self) -> None:
        self._service = None

    def is_configured(self) -> bool:
        return (
            Path(settings.YOUTUBE_CLIENT_SECRETS_FILE).exists()
            or Path(settings.YOUTUBE_TOKEN_FILE).exists()
        )

    def _get_service(self):
        if self._service:
            return self._service

        creds = None
        token_path = Path(settings.YOUTUBE_TOKEN_FILE)
        secrets_path = Path(settings.YOUTUBE_CLIENT_SECRETS_FILE)

        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not secrets_path.exists():
                    raise FileNotFoundError(
                        f"Missing {secrets_path}. Download OAuth client secrets "
                        "from Google Cloud Console and place the file in the project root."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(secrets_path), SCOPES
                )
                creds = flow.run_local_server(port=0)
            token_path.write_text(creds.to_json())

        self._service = build("youtube", "v3", credentials=creds)
        return self._service

    def publish(
        self,
        video_path: Path,
        title: str,
        description: str = "",
        tags: Optional[List[str]] = None,
        privacy_status: Optional[str] = None,
        category_id: str = "22",  # People & Blogs
        made_for_kids: bool = False,
        **kwargs: Any,
    ) -> PublishResult:
        if not video_path.exists():
            return PublishResult(
                platform=self.name,
                success=False,
                message=f"Video file not found: {video_path}",
            )

        # Ensure Shorts classification
        if "#Shorts" not in title and "#shorts" not in title.lower():
            title = f"{title} #Shorts"
        if "#Shorts" not in description and "#shorts" not in description.lower():
            description = (description + "\n\n#Shorts").strip()

        privacy = privacy_status or settings.YOUTUBE_PRIVACY_STATUS

        body = {
            "snippet": {
                "title": title[:100],  # YouTube limit
                "description": description[:5000],
                "tags": tags or ["Shorts", "AI", "automated"],
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": made_for_kids,
            },
        }

        try:
            youtube = self._get_service()
            media = MediaFileUpload(
                str(video_path),
                mimetype="video/mp4",
                resumable=True,
                chunksize=1024 * 1024 * 5,  # 5 MB chunks
            )
            request = youtube.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media,
            )
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    print(f"   YouTube upload progress: {int(status.progress() * 100)}%")

            video_id = response.get("id")
            url = f"https://www.youtube.com/watch?v={video_id}" if video_id else None
            return PublishResult(
                platform=self.name,
                success=True,
                post_id=video_id,
                url=url,
                message=f"Uploaded as Short → {url}",
                raw=response,
            )
        except HttpError as e:
            return PublishResult(
                platform=self.name,
                success=False,
                message=f"YouTube API error: {e}",
                raw={"error": str(e)},
            )
        except Exception as e:
            return PublishResult(
                platform=self.name,
                success=False,
                message=str(e),
            )
