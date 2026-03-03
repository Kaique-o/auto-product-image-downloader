class ImgGenError(Exception):
    """Base exception for the application."""
    pass

class ConfigError(ImgGenError):
    """Raised when there is a configuration error."""
    pass

class SpreadsheetError(ImgGenError):
    """Raised when there is an error reading or writing the spreadsheet."""
    pass

class SearchError(ImgGenError):
    """Raised when there is an error with the search API."""
    pass

class DownloadError(ImgGenError):
    """Raised when an image download fails."""
    pass

class ValidationError(ImgGenError):
    """Raised when image validation fails."""
    pass
