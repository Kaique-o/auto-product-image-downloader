import pytest
import httpx
import io
from pathlib import Path
from unittest.mock import MagicMock, patch
from openpyxl import Workbook
from PIL import Image

from imggen_app.infrastructure.spreadsheet.excel_openpyxl import ExcelHandler
from imggen_app.infrastructure.search.google_scraper import GoogleImageScraper
from imggen_app.infrastructure.http.rate_limiter import RateLimiter
from imggen_app.infrastructure.http.retry import with_retry
from imggen_app.infrastructure.cache.disk_cache import DiskCache
from imggen_app.domain.exceptions import SpreadsheetError, SearchError, ValidationError, DownloadError
from imggen_app.utils.image_utils import sanitize_filename, validate_and_convert_to_jpeg, get_bytes_hash

# --- Spreadsheet Tests ---

def test_read_spreadsheet_missing_columns(tmp_path):
    path = tmp_path / "bad_cols.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.append(["Wrong Header 1", "Wrong Header 2"])
    ws.append(["Desc", "Name"])
    wb.save(path)
    
    with pytest.raises(SpreadsheetError, match="Invalid headers"):
        list(ExcelHandler.read_rows(path))

def test_read_spreadsheet_empty_rows(tmp_path):
    path = tmp_path / "empty_rows.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.append(["Product Description", "Image Base Name"])
    ws.append(["P1", "N1"])
    ws.append([None, None]) # Empty row
    ws.append(["P2", "N2"])
    wb.save(path)
    
    rows = list(ExcelHandler.read_rows(path))
    assert len(rows) == 2
    assert rows[0].description == "P1"
    assert rows[1].description == "P2"

def test_read_spreadsheet_invalid_format(tmp_path):
    path = tmp_path / "not_excel.txt"
    path.write_text("hello")
    with pytest.raises(SpreadsheetError):
        list(ExcelHandler.read_rows(path))

# --- Image Utility Tests ---

def test_validate_image_corrupted():
    with pytest.raises(ValidationError):
        validate_and_convert_to_jpeg(b"corrupted data")

def test_filename_conflicts():
    # This logic is partly in the UseCase but sanitize helps
    assert sanitize_filename("CON") == "_CON_"
    assert sanitize_filename("test/file") == "testfile"

# --- Infrastructure Tests ---

def test_rate_limiter_burst():
    limiter = RateLimiter(requests_per_second=1.0) # 1 req/sec
    # First one immediate
    limiter.acquire_sync()
    
    import time
    start = time.monotonic()
    limiter.acquire_sync()
    end = time.monotonic()
    
    # Second one should take about 1 second
    assert 0.9 <= (end - start) <= 1.2

@patch("httpx.Client.get")
def test_google_scraper_search_error(mock_get):
    mock_get.side_effect = httpx.HTTPStatusError("Error", request=MagicMock(), response=MagicMock(status_code=500))
    client = GoogleImageScraper()
    
    with pytest.raises(SearchError):
        client.search_images("query")

def test_disk_cache_logic(tmp_path):
    cache = DiskCache(tmp_path)
    url = "https://example.com/img.jpg"
    data = b"image_data"
    
    assert cache.get(url) is None
    cache.set(url, data)
    assert cache.get(url) == data

# --- Retry Logic Tests ---

def test_retry_decorator_failures():
    attempts = 0
    
    @with_retry(max_attempts=3, backoff_base=0.01)
    def fail_func():
        nonlocal attempts
        attempts += 1
        raise httpx.ConnectError("Failed")
        
    with pytest.raises(httpx.ConnectError):
        fail_func()
    
    assert attempts == 3
