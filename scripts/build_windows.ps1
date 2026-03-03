# Build script for Windows
# Requires PyInstaller to be installed in the venv

$root = Get-Location
$venv = Join-Path $root ".venv"
$python = Join-Path $venv "Scripts\python.exe"
$pyinstaller = Join-Path $venv "Scripts\pyinstaller.exe"

if (-not (Test-Path $python)) {
    Write-Error "Virtual environment not found at $venv. Please run bootstrap first."
    exit 1
}

Write-Host "--- Starting Build Process ---"

# Install dev dependencies if needed
& $python -m pip install -e .[dev]

# Build using the spec file
Write-Host "Building One-Folder distribution..."
& $pyinstaller --noconfirm --clean packaging/pyinstaller.spec

Write-Host "Building One-File executable (optional)..."
& $pyinstaller --noconfirm --clean --onefile --windowed --name "AutoProductImageDownloader_Single" src/imggen_app/main.py

Write-Host "--- Build Complete! Check the 'dist' folder. ---"
