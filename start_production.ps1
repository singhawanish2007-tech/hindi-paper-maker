# ========================================================
# HINDI PAPER MAKER - PowerShell Production Launcher
# ========================================================
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $root

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "   HINDI PAPER MAKER (हिंदी प्रश्नपत्रिका निर्माता)" -ForegroundColor Yellow
Write-Host "   Unified Production Full-Stack Server" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

# Step 1: Check frontend build
if (-not (Test-Path "$root\frontend\dist\index.html")) {
    Write-Host "`n[1/3] Building frontend production bundle..." -ForegroundColor Green
    Set-Location "$root\frontend"
    npm run build
    Set-Location $root
} else {
    Write-Host "`n[1/3] Frontend build ready in frontend\dist." -ForegroundColor Green
}

# Step 2: Show network addresses
$localIP = (Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias "Wi-Fi*", "Ethernet*" -ErrorAction SilentlyContinue | Where-Object { $_.IPAddress -notlike "169.254*" -and $_.IPAddress -ne "127.0.0.1" } | Select-Object -First 1).IPAddress

Write-Host "`n[2/3] Access URLs:" -ForegroundColor Green
Write-Host "  - Local PC:       http://localhost:8000" -ForegroundColor White
if ($localIP) {
    Write-Host "  - School Network: http://${localIP}:8000" -ForegroundColor Yellow
}

# Step 3: Launch browser and server
Write-Host "`n[3/3] Launching production server..." -ForegroundColor Green
Start-Process "http://localhost:8000"
Set-Location "$root\backend"
& ".\.venv\Scripts\python.exe" main.py
