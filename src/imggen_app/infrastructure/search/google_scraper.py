import httpx
import logging
import re
import json
from bs4 import BeautifulSoup
from typing import Any
from imggen_app.domain.models import ImageResult
from imggen_app.domain.exceptions import SearchError
from imggen_app.infrastructure.http.retry import with_retry

logger = logging.getLogger(__name__)

class GoogleImageScraper:
    """
    Scrapes images using Yahoo Image Search.
    This replaces the Google dependency which is aggressively blocking scrapers.
    """
    def __init__(self, safe_search: str = "active"):
        self.safe_search = safe_search
        # Common desktop user agent
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        self.client = httpx.Client(timeout=20.0, follow_redirects=True)

    @with_retry()
    def search_images(self, query: str, count: int = 5) -> list[ImageResult]:
        """
        Executes an Image search and parses the result.
        """
        search_url = "https://images.search.yahoo.com/search/images"
        params = {
            "p": query,
        }
        
        try:
            response = self.client.get(search_url, headers=self.headers, params=params)
            response.raise_for_status()
            
            html = response.text
            
            soup = BeautifulSoup(html, "html.parser")
            results = []
            valid_urls = []
            
            # Extract high res URLs robustly using data-origurl attribute
            elements = soup.find_all(attrs={"data-origurl": True})
            for el in elements:
                orig_url = el.get("data-origurl")
                if orig_url and orig_url.startswith("http"):
                    valid_urls.append(orig_url)

            # Deduplicate and limit
            seen = set()
            for url in valid_urls:
                if url not in seen:
                    results.append(ImageResult(
                        url=url,
                        source_url="https://images.search.yahoo.com",
                        width=0, # Width/Height not always easily available from simple scrape
                        height=0,
                        content_type="image/jpeg",
                        thumbnail_url=url
                    ))
                    seen.add(url)
                    if len(results) >= count:
                        break
            
            if not results:
                logger.warning(f"No results found for query: {query}")
                
            return results
            
        except Exception as e:
            logger.error(f"Image Scrape failed for query '{query}': {e}")
            raise SearchError(f"Scrape failed: {e}") from e

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()
