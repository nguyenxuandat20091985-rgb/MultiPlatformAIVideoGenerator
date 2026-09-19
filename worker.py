"""Remote video worker entrypoint.

The worker reuses the same FastAPI/pipeline code as the main API but is
configured with WORKER_MODE=1 and a larger-memory host.
"""
from api import app

__all__ = ["app"]
