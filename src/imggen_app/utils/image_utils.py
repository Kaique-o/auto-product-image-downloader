import hashlib
import io
import re
from pathlib import Path
from PIL import Image
import logging
from imggen_app.domain.exceptions import ValidationError

logger = logging.getLogger(__name__)

def sanitize_filename(name: str) -> str:
    """
    Sanitize the base name for use as a filename.
    Removes illegal characters and prevents reserved Windows names.
    """
    # Remove illegal characters
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    # Remove control characters
    name = re.sub(r'[\x00-\x1f\x7f]', '', name)
    # Trim whitespace
    name = name.strip()
    
    # Check for reserved Windows names
    reserved = {
        "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
        "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
    }
    if name.upper() in reserved:
        name = f"_{name}_"
        
    if not name:
        name = "unnamed_product"
        
    return name

def validate_and_convert_to_jpeg(
    image_bytes: bytes, 
    min_bytes: int = 5120
) -> bytes:
    """
    Validates image bytes and converts to JPEG.
    """
    if len(image_bytes) < min_bytes:
        raise ValidationError(f"Image too small: {len(image_bytes)} bytes")
        
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.verify() # Verify structure
        
        # Re-open for processing as verify() closes the file
        img = Image.open(io.BytesIO(image_bytes))
        
        # Convert to RGB if needed
        if img.mode != 'RGB':
            img = img.convert('RGB')
            
        output = io.BytesIO()
        img.save(output, format="JPEG", quality=85)
        return output.getvalue()
    except Exception as e:
        raise ValidationError(f"Invalid image format: {e}")

def get_bytes_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
