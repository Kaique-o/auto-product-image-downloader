import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from platformdirs import user_cache_dir
from imggen_app.domain.exceptions import ConfigError

@dataclass(frozen=True)
class Settings:
    # Search Settings
    safe_search: str = "Moderate"
    images_per_product: int = 5
    
    # HTTP Settings
    http_timeout_s: int = 20
    rate_limit_rps: float = 2.0
    retry_max_attempts: int = 4
    retry_backoff_base_s: float = 0.8
    
    # Cache Settings
    cache_enabled: bool = True
    cache_dir: Path = Path(user_cache_dir("imggen_app", "Kaique")) / "images"
    
    # Image Settings
    min_image_bytes: int = 5120
    log_level: str = "INFO"

def load_settings() -> Settings:
    load_dotenv()
    
    raw_cache_dir = os.getenv("CACHE_DIR")
    cache_dir = Path(raw_cache_dir) if raw_cache_dir else Path(user_cache_dir("imggen_app", "Kaique")) / "images"
    
    return Settings(
        safe_search=os.getenv("SAFE_SEARCH", "Moderate"),
        images_per_product=int(os.getenv("IMAGES_PER_PRODUCT", "5")),
        http_timeout_s=int(os.getenv("HTTP_TIMEOUT_S", "20")),
        rate_limit_rps=float(os.getenv("RATE_LIMIT_RPS", "2.0")),
        retry_max_attempts=int(os.getenv("RETRY_MAX_ATTEMPTS", "4")),
        retry_backoff_base_s=float(os.getenv("RETRY_BACKOFF_BASE_S", "0.8")),
        cache_enabled=os.getenv("CACHE_ENABLED", "1") == "1",
        cache_dir=cache_dir,
        min_image_bytes=int(os.getenv("MIN_IMAGE_BYTES", "5120")),
        log_level=os.getenv("LOG_LEVEL", "INFO")
    )
