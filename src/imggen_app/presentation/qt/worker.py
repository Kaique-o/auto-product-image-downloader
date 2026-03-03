from pathlib import Path
from PySide6.QtCore import QThread, Signal
from imggen_app.domain.models import ProductRow, SessionSummary
from imggen_app.application.use_cases.generate_images import ImageGeneratorUseCase
from imggen_app.infrastructure.search.google_scraper import GoogleImageScraper
from imggen_app.infrastructure.http.rate_limiter import RateLimiter
from imggen_app.infrastructure.cache.disk_cache import DiskCache
from imggen_app.config.settings import Settings

class ImageWorker(QThread):
    """
    Qt Worker Thread that runs the image generation use case.
    """
    progress = Signal(int)
    log_msg = Signal(str)
    finished = Signal(SessionSummary)
    error = Signal(str)

    def __init__(
        self, 
        settings: Settings, 
        rows: list[ProductRow], 
        dest: Path
    ):
        super().__init__()
        self.settings = settings
        self.rows = rows
        self.dest = dest
        self.use_case: ImageGeneratorUseCase | None = None

    def run(self):
        """
        The heavy lifting happens here in a separate OS thread to keep the UI responsive.
        Initializes the stack and runs the generation use case.
        """
        try:
            # 1. Initialize Scraper (No API key needed)
            search_client = GoogleImageScraper(
                safe_search="active" if self.settings.safe_search != "Off" else "off"
            )
            
            # 2. Setup pacing component
            rate_limiter = RateLimiter(self.settings.rate_limit_rps)
            
            # 3. Setup caching if enabled
            cache = None
            if self.settings.cache_enabled:
                cache = DiskCache(self.settings.cache_dir)

            # 4. Initialize Use Case with cross-thread signal callbacks
            self.use_case = ImageGeneratorUseCase(
                search_client=search_client,
                settings=self.settings,
                rate_limiter=rate_limiter,
                cache=cache,
                # Signals are sent from the worker thread but processed in the UI thread
                progress_callback=self.progress.emit,
                log_callback=self.log_msg.emit
            )

            # 5. Execute process
            summary = self.use_case.execute(self.rows, self.dest)
            # Emit the results back to the MainWindow
            self.finished.emit(summary)
            
        except Exception as e:
            # Report any catastrophic thread failure
            self.error.emit(str(e))
        finally:
            # Ensure cleanup happens even on error
            if self.use_case:
                self.use_case.close()

    def cancel(self):
        if self.use_case:
            self.use_case.cancel()
