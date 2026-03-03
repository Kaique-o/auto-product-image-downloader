import time
import psutil
import os
from pathlib import Path
from unittest.mock import MagicMock
from imggen_app.application.use_cases.generate_images import ImageGeneratorUseCase
from imggen_app.domain.models import ProductRow, ImageResult
from imggen_app.config.settings import Settings
from imggen_app.infrastructure.http.rate_limiter import RateLimiter
import io
from PIL import Image

def generate_sample_image():
    img = Image.new('RGB', (100, 100), color='blue')
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG')
    return img_byte_arr.getvalue()

def run_stress_test(num_products: int, output_dir: Path):
    print(f"\n--- Starting Stress Test: {num_products} products ---")
    
    settings = Settings(
        bing_api_key="stress_key",
        bing_endpoint="https://api.test",
        images_per_product=5,
        cache_enabled=False,
        min_image_bytes=10
    )
    
    # Mock search client
    search_client = MagicMock()
    search_client.search_images.return_value = [
        ImageResult(url=f"http://test.com/{i}.jpg", source_url="s", width=100, height=100, content_type="jpg")
        for i in range(5)
    ]
    
    rate_limiter = RateLimiter(1000) # High rate for stress test speed
    
    use_case = ImageGeneratorUseCase(
        search_client=search_client,
        settings=settings,
        rate_limiter=rate_limiter
    )
    
    # Mock the HTTP download to avoid network
    image_data = generate_sample_image()
    use_case.client.get = MagicMock(return_value=MagicMock(content=image_data, status_code=200))
    
    rows = [
        ProductRow(row_index=i+2, description=f"Product {i}", base_name=f"p_{i}")
        for i in range(num_products)
    ]
    
    process = psutil.Process(os.getpid())
    start_mem = process.memory_info().rss / 1024 / 1024
    start_time = time.monotonic()
    
    summary = use_case.execute(rows, output_dir)
    
    end_time = time.monotonic()
    end_mem = process.memory_info().rss / 1024 / 1024
    
    print(f"Execution Time: {end_time - start_time:.2f}s")
    print(f"Memory Usage: {start_mem:.2f}MB -> {end_mem:.2f}MB (Delta: {end_mem - start_mem:.2f}MB)")
    print(f"Total Images: {summary.total_images_saved}")
    
    # Verify file count
    files = list(output_dir.glob("*.jpg"))
    assert len(files) == num_products * 5
    print("Verification: SUCCESS")

if __name__ == "__main__":
    temp_out = Path("tests/stress_output")
    temp_out.mkdir(parents=True, exist_ok=True)
    
    try:
        for n in [1, 10, 100]:
            run_stress_test(n, temp_out)
            # Cleanup
            for f in temp_out.iterdir(): f.unlink()
    finally:
        if temp_out.exists():
            import shutil
            shutil.rmtree(temp_out)
