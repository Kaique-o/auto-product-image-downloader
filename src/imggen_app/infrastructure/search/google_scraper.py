import httpx
import logging
import re
import json
import urllib.parse
from bs4 import BeautifulSoup
from typing import Any
from imggen_app.domain.models import ImageResult
from imggen_app.domain.exceptions import SearchError
from imggen_app.infrastructure.http.retry import with_retry

logger = logging.getLogger(__name__)

class YahooImageScraper:
    """Scrapes images using Yahoo Image Search."""
    def __init__(self, safe_search: str = "active"):
        self.safe_search = safe_search
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        }
        self.client = httpx.Client(timeout=20.0, follow_redirects=True)

    @with_retry()
    def search_images(self, query: str, count: int = 5) -> list[ImageResult]:
        search_url = "https://images.search.yahoo.com/search/images"
        params = {"p": query}
        try:
            response = self.client.get(search_url, headers=self.headers, params=params)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            results = []
            valid_urls = []
            
            elements = soup.find_all(attrs={"data-origurl": True})
            for el in elements:
                orig_url = el.get("data-origurl")
                if orig_url and orig_url.startswith("http"):
                    valid_urls.append(orig_url)

            seen = set()
            for url in valid_urls:
                if url not in seen:
                    results.append(ImageResult(
                        url=url, source_url="https://images.search.yahoo.com",
                        width=0, height=0, content_type="image/jpeg", thumbnail_url=url
                    ))
                    seen.add(url)
                    if len(results) >= count: break
            
            if not results:
                logger.warning(f"No Yahoo results found for query: {query}")
            return results
        except Exception as e:
            logger.error(f"Yahoo Scrape failed for query '{query}': {e}")
            raise SearchError(f"Scrape failed: {e}") from e

    def __enter__(self): return self
    def __exit__(self, exc_type, exc_val, exc_tb): self.client.close()

class GoogleImageScraper:
    """Scrapes images using basic Google Image Search HTML."""
    def __init__(self, safe_search: str = "active"):
        self.safe_search = safe_search
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        }
        self.client = httpx.Client(timeout=20.0, follow_redirects=True)

    @with_retry()
    def search_images(self, query: str, count: int = 5) -> list[ImageResult]:
        search_url = "https://www.google.com/search"
        params = {
            "q": query,
            "tbm": "isch",
            "safe": self.safe_search
        }
        try:
            response = self.client.get(search_url, headers=self.headers, params=params)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            results = []
            
            images = soup.find_all("img")
            seen = set()
            for img in images:
                src = img.get("src") or img.get("data-src")
                if src and src.startswith("http"):
                    if src not in seen:
                        results.append(ImageResult(
                            url=src, source_url="https://www.google.com",
                            width=0, height=0, content_type="image/jpeg", thumbnail_url=src
                        ))
                        seen.add(src)
                        if len(results) >= count: break
            
            if not results:
                logger.warning(f"No Google results found for query: {query}")
            return results
        except Exception as e:
            logger.error(f"Google Scrape failed for query '{query}': {e}")
            raise SearchError(f"Scrape failed: {e}") from e
            
    def __enter__(self): return self
    def __exit__(self, exc_type, exc_val, exc_tb): self.client.close()

class EbayImageScraper:
    """Scrapes images using eBay search."""
    def __init__(self, safe_search: str = "active"):
        self.safe_search = safe_search
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        }
        self.client = httpx.Client(timeout=20.0, follow_redirects=True)

    @with_retry()
    def search_images(self, query: str, count: int = 5) -> list[ImageResult]:
        search_url = "https://www.ebay.com/sch/i.html"
        params = {"_nkw": query}
        try:
            response = self.client.get(search_url, headers=self.headers, params=params)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            results = []
            
            images = soup.select(".s-item__image-img")
            seen = set()
            for img in images:
                src = img.get("src") or img.get("data-src")
                if src and src.startswith("http") and "ir.ebaystatic.com" not in src:
                    # try to get high res image
                    src = src.replace("s-l140", "s-l1000").replace("s-l225", "s-l1000").replace("s-l500", "s-l1000")
                    if src not in seen:
                        results.append(ImageResult(
                            url=src, source_url="https://www.ebay.com",
                            width=0, height=0, content_type="image/jpeg", thumbnail_url=src
                        ))
                        seen.add(src)
                        if len(results) >= count: break
            
            if not results:
                logger.warning(f"No eBay results found for query: {query}")
            return results
        except Exception as e:
            logger.error(f"eBay Scrape failed for query '{query}': {e}")
            raise SearchError(f"Scrape failed: {e}") from e
            
    def __enter__(self): return self
    def __exit__(self, exc_type, exc_val, exc_tb): self.client.close()

def get_scraper(engine_name: str, safe_search: str = "active"):
    """Factory to get the selected scraper engine."""
    engine_name = engine_name.lower().strip()
    if engine_name == "yahoo":
        return YahooImageScraper(safe_search=safe_search)
    elif engine_name == "google":
        return GoogleImageScraper(safe_search=safe_search)
    elif engine_name == "ebay":
        return EbayImageScraper(safe_search=safe_search)
    else:
        logger.warning(f"Unknown engine '{engine_name}', falling back to Yahoo")
        return YahooImageScraper(safe_search=safe_search)
