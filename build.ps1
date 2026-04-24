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

# --- Chromium ---
Write-Host "`n=== Installing Chromium for Playwright ===" -ForegroundColor Cyan
python -m playwright install chromium

# --- Stage Chromium for the installer ---
Write-Host "`n=== Staging Chromium ===" -ForegroundColor Cyan
if (Test-Path chromium_stage) { Remove-Item -Recurse -Force chromium_stage }
$src = "$env:LOCALAPPDATA\ms-playwright"
if (-not (Test-Path $src)) { throw "Chromium not found at $src" }
New-Item -ItemType Directory -Force -Path chromium_stage | Out-Null
Copy-Item -Recurse -Force "$src\*" chromium_stage\

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
