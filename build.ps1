# Local Windows build — mirrors .github/workflows/build.yml
# Run on the Windows VM after cloning: .\build.ps1 [-Version 0.1.0]
# Requires: Python 3.12+, Inno Setup 6 (install via `choco install innosetup`)

param(
    [string]$Version = "0.1.0-dev"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "=== StarPing local build ($Version) ===" -ForegroundColor Cyan

# --- Python deps ---
if (-not (Test-Path .venv)) {
    Write-Host "Creating venv..."
    python -m venv .venv
}
& .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

# --- Chromium (bundled into PyInstaller payload via bundled_browsers/) ---
Write-Host "`n=== Installing Chromium into bundled_browsers/ ===" -ForegroundColor Cyan
if (Test-Path bundled_browsers) { Remove-Item -Recurse -Force bundled_browsers }
$env:PLAYWRIGHT_BROWSERS_PATH = "$ProjectRoot\bundled_browsers"
python -m playwright install chromium
Remove-Item Env:PLAYWRIGHT_BROWSERS_PATH

# --- PyInstaller ---
Write-Host "`n=== PyInstaller ===" -ForegroundColor Cyan
if (Test-Path dist\StarPing) { Remove-Item -Recurse -Force dist\StarPing }
if (Test-Path build) { Remove-Item -Recurse -Force build }
pyinstaller --noconfirm starping.spec

# --- Inno Setup ---
Write-Host "`n=== Inno Setup ===" -ForegroundColor Cyan
$iscc = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $iscc)) {
    throw "Inno Setup not found. Install with: choco install innosetup"
}
& $iscc "/DAppVersion=$Version" installer.iss
if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed" }

$installer = "dist\StarPing-Setup.exe"
if (Test-Path $installer) {
    $size = (Get-Item $installer).Length / 1MB
    Write-Host "`n=== Done: $installer ($([math]::Round($size,1)) MB) ===" -ForegroundColor Green
} else {
    throw "Expected installer not found at $installer"
}
