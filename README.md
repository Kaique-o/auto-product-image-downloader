# Auto Product Image Downloader

A production-grade Python desktop application for batch-downloading product images based on Excel spreadsheet descriptions. **Now uses Google Images Scraping (No API keys required!)**

## Features
- **Modern GUI**: Built with PySide6 (Qt for Python).
- **Excel Integration**: Download templates and upload filled spreadsheets.
- **Free Image Search**: Uses robust Google Images scraping.
- **Robust Processing**:
  - Threaded execution (UI remains responsive).
  - Rate limiting and exponential backoff.
  - Image validation (Pillow) and conversion to JPEG.
  - Disk caching to avoid redundant downloads.
  - Robust error handling (skips failed rows, summarizes at the end).
- **Clean Architecture**: Modular code separation.

## Requirements
- Python 3.11+
- Internet Connection

## 🚀 Quickstart

Everything is automated for Windows users:

1. **Run**: Double-click **`run.bat`** in the root folder.
   - *This will automatically set up the virtual environment and install all dependencies (BeautifulSoup4, etc.) on the first run.*

2. **Launch**: The app will open immediately. No configuration or API keys needed!

## Usage Steps
1. **Download Template**: Click the button to save an `.xlsx` file with the required headers.
2. **Fill Spreadsheet**: Open the template and add your product descriptions and desired file base names.
3. **Upload Spreadsheet**: Select your filled file in the app.
4. **Select Destination**: Choose folder where images will be saved.
5. **Generate**: Click the button and watch the progress.

## Development
- **Linting**: `ruff check .`
- **Formatting**: `black .`
- **Type Checking**: `mypy src`
- **Testing**: `pytest`

## Packaging as EXE
To build a standalone Windows executable:
```powershell
.\scripts\build_windows.ps1
```

## License
MIT License. See `LICENSE` for details.

## Security & Legal Note
This tool uses web scraping. Ensure you comply with Google's Terms of Service. This tool is for educational and automation purposes; respect image copyright and licensing.
