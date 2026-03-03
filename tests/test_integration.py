import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
import httpx
import io
from PIL import Image

from imggen_app.application.use_cases.generate_images import ImageGeneratorUseCase
from imggen_app.domain.models import ProductRow
from imggen_app.config.settings import Settings
from imggen_app.infrastructure.http.rate_limiter import RateLimiter

@pytest.fixture
def mock_settings(tmp_path):
    return Settings(
        cache_enabled=False,
        min_image_bytes=10,
        images_per_product=2,
        cache_dir=tmp_path / "cache",
        safe_search="Moderate"
    )

@pytest.fixture
def sample_image():
    img = Image.new('RGB', (100, 100), color='red')
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG')
    return img_byte_arr.getvalue()

@patch("imggen_app.infrastructure.search.google_scraper.GoogleImageScraper.search_images")
@patch("httpx.Client.get")
def test_full_generate_flow(mock_http_get, mock_search, mock_settings, sample_image, tmp_path):
    # 1. Setup mocks
    from imggen_app.domain.models import ImageResult
    mock_search.return_value = [
        ImageResult(url="http://i.com/1.jpg", source_url="s1", width=100, height=100, content_type="jpg"),
        ImageResult(url="http://i.com/2.jpg", source_url="s2", width=100, height=100, content_type="jpg")
    ]
    
    mock_response = MagicMock()
    mock_response.content = sample_image
    mock_response.raise_for_status = MagicMock()
    mock_http_get.return_value = mock_response
    
    # 2. Setup Use Case
    search_client = MagicMock()
    search_client.search_images = mock_search
    rate_limiter = RateLimiter(100)
    
    use_case = ImageGeneratorUseCase(
        search_client=search_client,
        settings=mock_settings,
        rate_limiter=rate_limiter
    )
    
    # 3. Execute
    product_rows = [
        ProductRow(row_index=2, description="Product A", base_name="product_a")
    ]
    dest_folder = tmp_path / "output"
    
    summary = use_case.execute(product_rows, dest_folder)
    
    # 4. Assertions
    assert summary.total_rows == 1
    assert summary.successful_rows == 1
    assert summary.total_images_saved == 2
    
    # Check if files exist
    assert (dest_folder / "product_a_1.jpg").exists()
    assert (dest_folder / "product_a_2.jpg").exists()
    
    # Check content is at least present
    assert len((dest_folder / "product_a_1.jpg").read_bytes()) > 0
