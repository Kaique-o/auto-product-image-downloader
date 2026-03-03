import pytest
from pathlib import Path
from imggen_app.utils.image_utils import sanitize_filename, validate_and_convert_to_jpeg
from imggen_app.infrastructure.http.rate_limiter import RateLimiter
from imggen_app.domain.exceptions import ValidationError
import time
import io
from PIL import Image

def test_sanitize_filename():
    assert sanitize_filename("Normal Name") == "Normal Name"
    assert sanitize_filename("Name with /?*") == "Name with"
    assert sanitize_filename("CON") == "_CON_"
    assert sanitize_filename("  spaces  ") == "spaces"
    assert sanitize_filename("") == "unnamed_product"

def test_rate_limiter():
    limiter = RateLimiter(requests_per_second=10)
    start = time.monotonic()
    for _ in range(5):
        limiter.acquire_sync()
    duration = time.monotonic() - start
    # Should be very fast (less than 0.5s)
    assert duration < 0.6

def test_image_validation_valid():
    # Create a small valid image
    img = Image.new('RGB', (100, 100), color='red')
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG')
    valid_bytes = img_byte_arr.getvalue()
    
    # We set min_bytes small for test
    result = validate_and_convert_to_jpeg(valid_bytes, min_bytes=10)
    assert isinstance(result, bytes)
    assert len(result) > 0

def test_image_validation_invalid():
    with pytest.raises(ValidationError):
        validate_and_convert_to_jpeg(b"not an image", min_bytes=0)

def test_image_validation_too_small():
    img = Image.new('RGB', (10, 10), color='blue')
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG')
    
    with pytest.raises(ValidationError):
        validate_and_convert_to_jpeg(img_byte_arr.getvalue(), min_bytes=100000)
