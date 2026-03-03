# Testing Strategy - Auto Product Image Downloader

This document outlines the comprehensive testing strategy for the Auto Product Image Downloader application, covering unit, integration, stress, usability, and security testing.

## 1. Unit Testing
**Tool**: `pytest`
**Target Coverage**: 80%+

### Coverage Areas:
- **Spreadsheet Parsing**:
  - Valid `.xlsx` loading.
  - Empty rows (should skip).
  - Invalid file formats (e.g., `.txt`, `.csv`).
  - Missing or renamed columns.
  - Formula cells and special characters.
- **Image Processing**:
  - Invalid image URLs (404, 500).
  - Corrupted image bytes (invalid formats).
  - Normalization to JPEG.
  - Size validation (min bytes).
- **Infrastructure**:
  - **Retry Logic**: Exponential backoff verification.
  - **Rate Limiting**: Token bucket behavior under pressure.
  - **Caching**: Hit/miss logic and disk persistence.
- **Utilities**:
  - Filename sanitization (Windows reserved names, length).
  - File naming conflicts (duplication handling).

## 2. Integration Testing
Validates the interaction between components using mocked external APIs.

### Scenarios:
- **End-to-End Mock Flow**:
  1. Load a sample spreadsheet.
  2. Simulate Bing API response with hardcoded URLs.
  3. Simulate file downloads using local mock data.
  4. Verify files are saved in the correct destination with the `{base}_{num}.jpg` format.
  5. Validate folder creation if it doesn't exist.

## 3. Stress & Load Testing
**Script**: `tests/test_stress.py`

### Metrics:
- **Product Scaling**: Test with 1, 10, 100, and 1000 product rows.
- **Performance**: Measure execution time and memory consumption (using `psutil`).
- **Stability**: Ensure the UI thread remains responsive (no "Not Responding" state).
- **Concurrency**: Validate that the rate limiter correctly manages high-frequency requests.

## 4. Break Tests (Destructive Testing)
Intentional attempts to crash the system.

### Scenarios:
- **Data Edge Cases**: 10,000+ rows, 500+ character descriptions, emojis in product names.
- **Network Instability**: Simulate complete loss of internet mid-process.
- **API Failure**: Simulate 429 (Too Many Requests), 500 (Server Error), and malformed JSON responses.
- **System Constraints**:
  - Folder without write permissions.
  - Disk full simulation.
  - Interrupted downloads.

## 5. Usability Testing
- **Navigation**: Verify 1-click template download.
- **Intuition**: Ensure folder selection and upload buttons are clearly labeled.
- **Feedback**:
  - Progress bar reflects real-time status.
  - Logs are auto-scrolling and readable.
  - Error messages are friendly (e.g., "Invalid API Key" instead of a stack trace).
- **Guardrails**: "Generate" button remains disabled until all inputs are valid.

## 6. Manual QA Checklist
1. **Fresh Install**: Run `bootstrap.py`, verify `.env` requirement.
2. **Standard Workflow**: Download template -> Fill -> Upload -> Select Folder -> Generate.
3. **Cancellation**: Click "Cancel" at 50% progress. Verify cleanup.
4. **Collision**: Run the same spreadsheet twice into the same folder. Verify `_r{row}` suffix.
5. **Hard-kill**: Close the app mid-download. Verify no corrupted partial files remain.

## 7. Performance & Security
- **Optimization**: The current implementation uses synchronous `httpx` in a worker thread. For higher scale, a thread pool or `asyncio` loop within the worker thread could be used.
- **Sanitization**: All filenames are stripped of illegal characters to prevent path traversal.
- **Secrets**: API keys are isolated in `.env` and excluded via `.gitignore`.
- **Injection**: Spreadsheet reading is restricted to data values (using `data_only=True` in `openpyxl`).

## 9. How to Run Tests

### Prerequisites
Ensure dev dependencies are installed:
```powershell
pip install -e .[dev]
```

### Run Unit & Integration Tests
```powershell
pytest
```

### Run with Coverage
```powershell
pytest --cov=src --cov-report=term-missing
```

### Run Stress Test
```powershell
python tests/test_stress.py
```

### Run Specialized Break Tests
```powershell
pytest tests/test_break.py
```

## 10. Performance Optimization Roadmap
- **Asyncio Integration**: Swap `httpx.Client` for `httpx.AsyncClient` and use `asyncio.gather` for downloading images of a single product concurrently.
- **Connection Pooling**: Reuse HTTP connections across product rows to reduce SSL handshake overhead.
- **Bulk Save**: Use a buffer to write images in chunks if dealing with extremely slow disks.
