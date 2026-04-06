import httpx
import logging
import re
import json
import urllib.parse
from bs4 import BeautifulSoup
from typing import Any, Dict, List, Optional
from imggen_app.domain.models import ImageResult
from imggen_app.domain.exceptions import SearchError
from imggen_app.infrastructure.http.retry import with_retry

logger = logging.getLogger(__name__)

# Very stable User-Agent
DEFAULT_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"

def get_headers(engine: str = "google") -> Dict[str, str]:
    """Provides stable headers for scraping."""
    return {
        "User-Agent": DEFAULT_UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": f"https://www.{engine}.com/",
    }

class BingImageScraper:
    """A highly reliable and lenient scraper for high-res images."""
    def __init__(self, safe_search: str = "active"):
        self.client = httpx.Client(timeout=15.0, follow_redirects=True, headers={"User-Agent": DEFAULT_UA})

    def search_images(self, query: str, count: int = 5) -> List[ImageResult]:
        try:
            url = f"https://www.bing.com/images/search?q={urllib.parse.quote(query)}"
            res = self.client.get(url)
            if res.status_code != 200: return []
            
            # Bing uses "murl" in a JSON blob for the high-res image URL
            results = []
            pattern = re.compile(r'murl&quot;:&quot;(http[^&]+)&quot;')
            matches = pattern.findall(res.text)
            
            for img_url in matches:
                # Clean up URL (sometimes has html entities)
                img_url = img_url.replace("\\/", "/")
                results.append(ImageResult(
                    url=img_url, source_url="https://www.bing.com",
                    width=0, height=0, content_type="image/jpeg", 
                    thumbnail_url=img_url
                ))
                if len(results) >= count: break
            return results
        except Exception as e:
            logger.error(f"Bing scraper failed: {e}")
            return []
            
    def __enter__(self): return self
    def __exit__(self, *args): self.client.close()

class DuckDuckGoScraper:
    """DuckDuckGo scraper used as secondary fallback."""
    def __init__(self, safe_search: str = "active"):
        self.client = httpx.Client(timeout=15.0, follow_redirects=True, headers={"User-Agent": DEFAULT_UA})

    def search_images(self, query: str, count: int = 5) -> List[ImageResult]:
        try:
            vqd_url = "https://duckduckgo.com/"
            vqd_res = self.client.get(vqd_url, params={"q": query})
            vqd_match = re.search(r'vqd=([^&\'"]+)', vqd_res.text)
            if not vqd_match: return []
            vqd = vqd_match.group(1)

            search_url = "https://duckduckgo.com/i.js"
            params = {"l": "wt-wt", "o": "json", "q": query, "vqd": vqd, "f": ",,,", "p": "1"}
            res = self.client.get(search_url, params=params)
            if res.status_code != 200: return []
            
            data = res.json()
            results = []
            for item in data.get("results", []):
                results.append(ImageResult(
                    url=item["image"], source_url=item.get("url", "https://duckduckgo.com"),
                    width=item.get("width", 0), height=item.get("height", 0),
                    content_type="image/jpeg", thumbnail_url=item.get("thumbnail", item["image"])
                ))
                if len(results) >= count: break
            return results
        except:
            return []
    
    def __enter__(self): return self
    def __exit__(self, *args): self.client.close()

class YahooImageScraper:
    """Scrapes Yahoo with Bing fallback."""
    def __init__(self, safe_search: str = "active"):
        self.safe_search = safe_search
        self.client = httpx.Client(timeout=30.0, follow_redirects=True)

    @with_retry()
    def search_images(self, query: str, count: int = 5) -> List[ImageResult]:
        try:
            search_url = "https://images.search.yahoo.com/search/images"
            response = self.client.get(search_url, headers=get_headers("yahoo"), params={"p": query})
            results = []
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                elements = soup.find_all(attrs={"data-origurl": True})
                for el in elements:
                    results.append(ImageResult(url=el.get("data-origurl"), source_url="https://images.search.yahoo.com", width=0, height=0, content_type="image/jpeg", thumbnail_url=el.get("data-origurl")))
                    if len(results) >= count: break
            
            if not results:
                logger.info(f"Yahoo failed, falling back to Bing for {query}")
                with BingImageScraper() as bing:
                    return bing.search_images(query, count)
            return results
        except Exception:
            with BingImageScraper() as bing:
                return bing.search_images(query, count)

    def __enter__(self): return self
    def __exit__(self, *args): self.client.close()

class GoogleImageScraper:
    """Scrapes Google with Bing fallback."""
    def __init__(self, safe_search: str = "active"):
        self.safe_search = safe_search
        self.client = httpx.Client(timeout=30.0, follow_redirects=True)

    @with_retry()
    def search_images(self, query: str, count: int = 5) -> List[ImageResult]:
        try:
            search_url = "https://www.google.com/search"
            response = self.client.get(search_url, headers=get_headers("google"), params={"q": query, "udm": "2"})
            results = []
            if response.status_code == 200 and "enablejs" not in response.text:
                soup = BeautifulSoup(response.text, "html.parser")
                links = soup.find_all("a", href=lambda x: x and "/imgres?" in x)
                for link in links:
                    img_url = urllib.parse.parse_qs(urllib.parse.urlparse(link.get("href")).query).get("imgurl", [None])[0]
                    if img_url:
                        results.append(ImageResult(url=img_url, source_url="https://www.google.com", width=0, height=0, content_type="image/jpeg", thumbnail_url=img_url))
                        if len(results) >= count: break
            
            if not results:
                logger.info(f"Google blocked, falling back to Bing for {query}")
                with BingImageScraper() as bing:
                    return bing.search_images(query, count)
            return results
        except Exception:
            with BingImageScraper() as bing:
                return bing.search_images(query, count)

    def __enter__(self): return self
    def __exit__(self, *args): self.client.close()

class EbayImageScraper:
    """Scrapes eBay with Bing fallback."""
    def __init__(self, safe_search: str = "active"):
        self.safe_search = safe_search
        self.client = httpx.Client(timeout=30.0, follow_redirects=True)

    @with_retry()
    def search_images(self, query: str, count: int = 5) -> List[ImageResult]:
        try:
            search_url = "https://www.ebay.com/sch/i.html"
            response = self.client.get(search_url, headers=get_headers("ebay"), params={"_nkw": query})
            results = []
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                items = soup.select(".s-item__image-wrapper img, .s-item img")
                for img in items:
                    src = img.get("data-src") or img.get("src")
                    if src and src.startswith("http") and "ebaystatic" not in src:
                        high_res = re.sub(r's-l\d+', 's-l1600', src)
                        results.append(ImageResult(url=high_res, source_url="https://www.ebay.com", width=0, height=0, content_type="image/jpeg", thumbnail_url=high_res))
                        if len(results) >= count: break
            
            if not results:
                logger.info(f"eBay failed, falling back to Bing for {query}")
                with BingImageScraper() as bing:
                    return bing.search_images(f"product {query} ebay", count)
            return results
        except Exception:
            with BingImageScraper() as bing:
                return bing.search_images(f"product {query} ebay", count)

    def __enter__(self): return self
    def __exit__(self, *args): self.client.close()

def get_scraper(engine_name: str, safe_search: str = "active"):
    """Global factory for all image scraping engines."""
    engine_name = engine_name.lower().strip()
    if engine_name == "yahoo":
        return YahooImageScraper(safe_search=safe_search)
    elif engine_name == "google":
        return GoogleImageScraper(safe_search=safe_search)
    elif engine_name == "ebay":
        return EbayImageScraper(safe_search=safe_search)
    else:
        return BingImageScraper(safe_search=safe_search)
