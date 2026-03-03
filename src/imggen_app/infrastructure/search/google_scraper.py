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
    Scrapes Google Images search results using httpx and BeautifulSoup.
    This replaces the Bing API dependency.
    """
    def __init__(self, safe_search: str = "active"):
        self.safe_search = safe_search
        # Common desktop user agent
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.google.com/"
        }
        self.client = httpx.Client(timeout=20.0, follow_redirects=True)

    @with_retry()
    def search_images(self, query: str, count: int = 5) -> list[ImageResult]:
        """
        Executes a Google Images search and parses the result.
        """
        search_url = "https://www.google.com/search"
        params = {
            "q": query,
            "tbm": "isch", # Image search
            "safe": self.safe_search
        }
        
        try:
            response = self.client.get(search_url, headers=self.headers, params=params)
            response.raise_for_status()
            
            # Simple parsing: Google uses some JS but also includes metadata in the HTML
            # Newer Google Images pages store image data in JSON-like blocks in <script> tags
            # We look for metadata patterns or standard <img> tags for thumbnails
            
            soup = BeautifulSoup(response.text, "html.parser")
            results = []
            
            # Pattern for original image URLs in modern Google search
            # Often found in AF_initDataCallback or similar blobs
            # We'll use a regex to find all URL patterns that look like images
            
            # Fallback strategy: Extract from simple <img> tags if JS parsing fails
            img_tags = soup.find_all("img")
            
            # Modern Google Images often embeds data in a script tag with data like [ "https://...", width, height ]
            # We'll try to find these JSON-like structures
            data_blocks = re.findall(r"\[\"(http[^\"]+?)\",\d+,\d+\]", response.text)
            
            valid_urls = [url for url in data_blocks if any(url.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp"])]
            
            if not valid_urls:
                # Fallback to thumbnails if direct URLs aren't found
                for img in img_tags:
                    src = img.get("src") or img.get("data-src")
                    if src and src.startswith("http"):
                        valid_urls.append(src)

            # Deduplicate and limit
            seen = set()
            for url in valid_urls:
                if url not in seen:
                    results.append(ImageResult(
                        url=url,
                        source_url="https://www.google.com",
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
            logger.error(f"Google Scrape failed for query '{query}': {e}")
            raise SearchError(f"Scrape failed: {e}") from e

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()
