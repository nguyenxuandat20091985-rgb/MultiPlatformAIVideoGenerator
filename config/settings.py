"""
Central configuration loaded from environment variables.
Paths are resolved relative to the project root so Docker / Hugging Face Spaces work.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")


def _path_from_env(env_key: str, default_relative: str) -> Path:
    raw = Path(os.getenv(env_key, default_relative))
    if not raw.is_absolute():
        raw = _PROJECT_ROOT / raw
    return raw


class Settings:
    # Core AI
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    TOGETHER_API_KEY: str = os.getenv("TOGETHER_API_KEY", "")

    # YouTube
    YOUTUBE_CLIENT_SECRETS_FILE: str = os.getenv(
        "YOUTUBE_CLIENT_SECRETS_FILE", "client_secrets.json"
    )
    YOUTUBE_TOKEN_FILE: str = os.getenv("YOUTUBE_TOKEN_FILE", "token.json")
    YOUTUBE_PRIVACY_STATUS: str = os.getenv("YOUTUBE_PRIVACY_STATUS", "public")

    # TikTok
    TIKTOK_ACCESS_TOKEN: str = os.getenv("TIKTOK_ACCESS_TOKEN", "")
    TIKTOK_PRIVACY_LEVEL: str = os.getenv(
        "TIKTOK_PRIVACY_LEVEL", "PUBLIC_TO_EVERYONE"
    )

    # Facebook
    FACEBOOK_PAGE_ID: str = os.getenv("FACEBOOK_PAGE_ID", "")
    FACEBOOK_PAGE_ACCESS_TOKEN: str = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN", "")
    FACEBOOK_API_VERSION: str = os.getenv("FACEBOOK_API_VERSION", "v21.0")

    # Runtime
    DEFAULT_VIDEO_STYLE: str = os.getenv("DEFAULT_VIDEO_STYLE", "educational")
    DEFAULT_TARGET_AUDIENCE: str = os.getenv("DEFAULT_TARGET_AUDIENCE", "general")
    DEFAULT_CTA: str = os.getenv("DEFAULT_CTA", "Follow for more!")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    PROJECT_ROOT: Path = _PROJECT_ROOT
    OUTPUT_DIR: Path = _path_from_env("OUTPUT_DIR", "output")

    @classmethod
    def validate_generation(cls) -> None:
        missing = []
        if not cls.GROQ_API_KEY:
            missing.append("GROQ_API_KEY")
        if not cls.TOGETHER_API_KEY:
            missing.append("TOGETHER_API_KEY")
        if missing:
            raise ValueError(
                "Missing required environment variables for video generation: "
                f"{', '.join(missing)}. "
                "Set them as Hugging Face Space Secrets or in a local .env file."
            )

    @classmethod
    def has_youtube(cls) -> bool:
        secrets = _path_from_env("YOUTUBE_CLIENT_SECRETS_FILE", "client_secrets.json")
        token = _path_from_env("YOUTUBE_TOKEN_FILE", "token.json")
        return secrets.exists() or token.exists()

    @classmethod
    def has_tiktok(cls) -> bool:
        return bool(cls.TIKTOK_ACCESS_TOKEN)

    @classmethod
    def has_facebook(cls) -> bool:
        return bool(cls.FACEBOOK_PAGE_ID and cls.FACEBOOK_PAGE_ACCESS_TOKEN)


settings = Settings()
settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
