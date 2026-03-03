import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional

def configure_logging(log_level: str = "INFO", ui_handler: Optional[logging.Handler] = None):
    """
    Configures logging for the application.
    """
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / "app.log"
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Clear existing handlers
    root_logger.handlers = []
    
    # File handler
    file_handler = RotatingFileHandler(
        log_file, maxBytes=10**6, backupCount=5, encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # UI handler if provided
    if ui_handler:
        ui_handler.setFormatter(formatter)
        root_logger.addHandler(ui_handler)
    
    logging.info("Logging configured.")
