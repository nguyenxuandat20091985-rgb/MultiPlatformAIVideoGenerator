"""Abstract base for all platform publishers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class PublishResult:
    platform: str
    success: bool
    post_id: Optional[str] = None
    url: Optional[str] = None
    message: str = ""
    raw: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        status = "✅" if self.success else "❌"
        return f"{status} [{self.platform}] {self.message or self.post_id or self.url or 'done'}"


class BasePublisher(ABC):
    """
    Every platform publisher must implement `publish`.
    This design makes it easy to add new networks later
    (Instagram, LinkedIn, X, Threads, etc.).
    """

    name: str = "base"

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True if credentials / tokens needed by this publisher are present."""
        ...

    @abstractmethod
    def publish(
        self,
        video_path: Path,
        title: str,
        description: str = "",
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> PublishResult:
        """
        Upload and publish the video.
        Implementations should be idempotent where possible and raise only on
        unrecoverable errors (or return PublishResult(success=False)).
        """
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} configured={self.is_configured()}>"
