import hashlib
import os
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class DiskCache:
    """
    Simple disk cache for image files.
    """
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, url: str) -> Path:
        url_hash = hashlib.sha256(url.encode('utf-8')).hexdigest()
        return self.cache_dir / url_hash

    def get(self, url: str) -> Optional[bytes]:
        path = self._get_path(url)
        if path.exists():
            try:
                return path.read_bytes()
            except Exception as e:
                logger.error(f"Failed to read from cache: {e}")
        return None

    def set(self, url: str, data: bytes) -> None:
        path = self._get_path(url)
        try:
            path.write_bytes(data)
        except Exception as e:
            logger.error(f"Failed to write to cache: {e}")

    def clear(self):
        """Clears all cached items."""
        for item in self.cache_dir.iterdir():
            if item.is_file():
                item.unlink()
