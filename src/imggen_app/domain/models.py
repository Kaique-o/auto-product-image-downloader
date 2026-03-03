from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

@dataclass(frozen=True)
class ProductRow:
    row_index: int
    description: str
    base_name: str

@dataclass(frozen=True)
class ImageResult:
    url: str
    source_url: str
    width: int
    height: int
    content_type: str
    thumbnail_url: Optional[str] = None

class Status(Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class ProcessingResult:
    product: ProductRow
    status: Status
    images_saved: int = 0
    errors: list[str] = field(default_factory=list)
    
@dataclass
class SessionSummary:
    total_rows: int = 0
    successful_rows: int = 0
    failed_rows: int = 0
    total_images_saved: int = 0
    errors: list[str] = field(default_factory=list)
