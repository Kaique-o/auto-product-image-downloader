import logging
import time
from pathlib import Path
from typing import Callable, Optional, Iterator, Protocol
import httpx

from imggen_app.domain.models import (
    ProductRow, 
    ImageResult, 
    ProcessingResult, 
    Status, 
    SessionSummary
)
from imggen_app.domain.exceptions import ImgGenError, SearchError, DownloadError, ValidationError

class ImageSearchPort(Protocol):
    def search_images(self, query: str, count: int = 5) -> list[ImageResult]:
        ...

from imggen_app.infrastructure.http.rate_limiter import RateLimiter
from imggen_app.infrastructure.cache.disk_cache import DiskCache
from imggen_app.utils.image_utils import sanitize_filename, validate_and_convert_to_jpeg
from imggen_app.config.settings import Settings

logger = logging.getLogger(__name__)

class ImageGeneratorUseCase:
    """
    Orchestrates the process of searching, downloading, validating, and saving images.
    This class is the core of the application's business logic.
    """
    def __init__(
        self,
        search_client: ImageSearchPort,
        settings: Settings,
        rate_limiter: RateLimiter,
        cache: Optional[DiskCache] = None,
        progress_callback: Optional[Callable[[int], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ):
        self.search_client = search_client
        self.settings = settings
        self.rate_limiter = rate_limiter
        self.cache = cache
        self.progress_callback = progress_callback
        self.log_callback = log_callback
        self.is_cancelled = False
        
        # Initialize internal HTTP client for image downloads
        self.client = httpx.Client(timeout=float(settings.http_timeout_s))

    def cancel(self):
        """Sets the cancellation flag to stop processing as soon as possible."""
        self.is_cancelled = True

    def _log(self, message: str):
        """Internal helper to log to standard logger and trigger UI callback."""
        logger.info(message)
        if self.log_callback:
            self.log_callback(message)

    def execute(
        self, 
        product_rows: list[ProductRow], 
        destination_folder: Path
    ) -> SessionSummary:
        """
        Main execution loop for a batch of products.
        Iterates over the spreadsheet rows and processes each one.
        """
        summary = SessionSummary(total_rows=len(product_rows))
        
        # Ensure the output directory exists before starting
        try:
            destination_folder.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            msg = f"Failed to create destination folder: {e}"
            self._log(msg)
            summary.failed_rows = len(product_rows)
            summary.errors.append(msg)
            return summary
        
        for i, product in enumerate(product_rows):
            # Check for user cancellation between products
            if self.is_cancelled:
                self._log("Process cancelled by user.")
                break
                
            self._log(f"Processing row {product.row_index}: {product.description}")
            
            try:
                # Process the individual product (search -> download -> save)
                result = self._process_product(product, destination_folder)
                
                if result.status == Status.SUCCESS:
                    summary.successful_rows += 1
                else:
                    summary.failed_rows += 1
                    summary.errors.extend(result.errors)
                    
                summary.total_images_saved += result.images_saved
                
            except Exception as e:
                # Robust catch-all to prevent one row from stopping the entire batch
                logger.exception(f"Unexpected error processing product {product.description}")
                summary.failed_rows += 1
                summary.errors.append(f"Row {product.row_index}: {str(e)}")
            
            # Trigger progress bar update via callback
            if self.progress_callback:
                progress = int(((i + 1) / len(product_rows)) * 100)
                self.progress_callback(progress)
                
        return summary

    def _process_product(self, product: ProductRow, dest: Path) -> ProcessingResult:
        """
        Handles the lifecycle of a single product's image generation.
        1. Search for image URLs
        2. Download bytes (with optional caching)
        3. Validate and convert to JPEG
        4. Save to disk
        """
        result = ProcessingResult(product=product, status=Status.PENDING)
        
        try:
            # 1. Search (Rate limited)
            self.rate_limiter.acquire_sync()
            images = self.search_client.search_images(
                product.description, 
                count=self.settings.images_per_product
            )
            
            if not images:
                self._log(f"No images found for: {product.description}")
                result.status = Status.FAILED
                result.errors.append(f"Row {product.row_index}: No images found.")
                return result

            # 2. Download and Save Loop
            # Sanitize the filename to remove illegal system characters
            base_name_sanitized = sanitize_filename(product.base_name)
            saved_count = 0
            
            for j, img_info in enumerate(images, start=1):
                if self.is_cancelled: break
                
                try:
                    # Check the local disk cache first
                    img_data = None
                    if self.settings.cache_enabled and self.cache:
                        img_data = self.cache.get(img_info.url)
                        if img_data:
                            self._log(f"  Using cached image for {img_info.url}")
                    
                    # Download from the web if not cached
                    if not img_data:
                        self._log(f"  Downloading: {img_info.url}")
                        resp = self.client.get(img_info.url)
                        resp.raise_for_status()
                        img_data = resp.content
                        
                        # Populate cache for future runs
                        if self.settings.cache_enabled and self.cache:
                            self.cache.set(img_info.url, img_data)

                    # Validate format and convert to standard JPEG (removing transparency etc)
                    jpeg_data = validate_and_convert_to_jpeg(
                        img_data, 
                        min_bytes=self.settings.min_image_bytes
                    )
                    
                    # Construct save path
                    file_name = f"{base_name_sanitized}_{j}.jpg"
                    file_path = dest / file_name
                    
                    # Handle naming collisions in the same folder by appending row index
                    if file_path.exists():
                         file_name = f"{base_name_sanitized}_r{product.row_index}_{j}.jpg"
                         file_path = dest / file_name
                         
                    file_path.write_bytes(jpeg_data)
                    saved_count += 1
                    
                except Exception as e:
                    # Log the specific image error but continue to the next candidate
                    msg = f"  Error downloading/validating image {j}: {e}"
                    self._log(msg)
                    result.errors.append(msg)
                    continue

            result.images_saved = saved_count
            if saved_count > 0:
                result.status = Status.SUCCESS
                self._log(f"  Successfully saved {saved_count} images for {product.description}")
            else:
                result.status = Status.FAILED
                result.errors.append(f"Row {product.row_index}: All image downloads failed.")
                
        except SearchError as e:
            msg = f"Search error for {product.description}: {e}"
            self._log(msg)
            result.status = Status.FAILED
            result.errors.append(msg)
        except Exception as e:
            msg = f"Error processing {product.description}: {e}"
            self._log(msg)
            result.status = Status.FAILED
            result.errors.append(msg)
            
        return result

    def close(self):
        """Cleanup resources."""
        self.client.close()
