import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
import httpx
import io
from PIL import Image
from imggen_app.application.use_cases.generate_images import ImageGeneratorUseCase
from imggen_app.infrastructure.spreadsheet.excel_openpyxl import ExcelHandler
from imggen_app.domain.models import ProductRow
from imggen_app.config.settings import Settings
from imggen_app.infrastructure.http.rate_limiter import RateLimiter

@pytest.fixture
def use_case(tmp_path):
    settings = Settings(
        cache_enabled=False,
        safe_search="Moderate"
    )
    search_client = MagicMock()
    rate_limiter = RateLimiter(100)
    return ImageGeneratorUseCase(search_client, settings, rate_limiter)

def test_break_disk_full(use_case, tmp_path, monkeypatch):
    # Simulate disk full error when writing bytes
    def mock_write_bytes(self, data):
        raise OSError(28, "No space left on device")
    
    monkeypatch.setattr(Path, "write_bytes", mock_write_bytes)
    
    # Ensure validation passes by using larger data or disabling min check
    use_case.settings = Settings(
        cache_enabled=False,
        min_image_bytes=0, # Disable min size check
        safe_search="Moderate"
    )

    product = ProductRow(row_index=2, description="P", base_name="N")
    
    # We mock search to return one image
    use_case.search_client.search_images.return_value = [MagicMock(url="http://i.com")]
    
    # Create a valid minimal JPEG for the mock
    img = Image.new('RGB', (10, 10), color='blue')
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG')
    valid_jpeg = img_byte_arr.getvalue()
    
    use_case.client.get = MagicMock(return_value=MagicMock(content=valid_jpeg, status_code=200))
    
    result = use_case._process_product(product, tmp_path)
    assert result.status.name == "FAILED"
    assert "No space left on device" in str(result.errors)

def test_break_api_malformed_json(use_case, tmp_path):
    # Search client handles JSON, let's mock it raising an error
    use_case.search_client.search_images.side_effect = Exception("Malformed JSON")
    
    product = ProductRow(row_index=2, description="P", base_name="N")
    result = use_case._process_product(product, tmp_path)
    
    assert result.status.name == "FAILED"
    assert "Malformed JSON" in str(result.errors)

def test_break_unwritable_folder(use_case, tmp_path):
    # Create a read-only folder
    ro_folder = tmp_path / "readonly"
    ro_folder.mkdir()
    
    # On Windows, setting read-only for folders is tricky, 
    # but we can mock the failure.
    with patch.object(Path, "mkdir", side_effect=PermissionError("Permission denied")):
        summary = use_case.execute([ProductRow(1, "D", "B")], ro_folder)
        assert summary.failed_rows == 1
        assert "Permission denied" in summary.errors[0]

def test_break_very_long_description(use_case, tmp_path):
    long_desc = "A" * 1000
    product = ProductRow(row_index=2, description=long_desc, base_name="normal")
    
    use_case.search_client.search_images.return_value = []
    result = use_case._process_product(product, tmp_path)
    
    # Should just handle it (API might return empty results)
    assert result.status.name == "FAILED"
    assert "No images found" in str(result.errors)
