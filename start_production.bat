@echo off
chcp 65001 > nul
title HINDI PAPER MAKER - Production Server

echo ========================================================
echo        HINDI PAPER MAKER (????? ????????????? ????????)
echo        Unified Production Full-Stack Server
echo ========================================================
echo.

cd /d "%~dp0"

REM Step 1: Check frontend build
if not exist "frontend\dist\index.html" (
    echo [1/3] Building frontend production bundle...
    cd frontend
    call npm run build
    if errorlevel 1 (
        echo ERROR: Frontend build failed.
        pause
        exit /b 1
    )
    cd ..
) else (
    echo [1/3] Frontend build found in frontend\dist.
)

REM Step 2: Show local network IP
echo.
echo [2/3] Local and Network Access Addresses:
echo   - Local PC:       http://localhost:8000
for /f "tokens=4" %%a in ('route print ^| find " 0.0.0.0 "') do (
    echo   - School Network: http://%%a:8000
    goto :found_ip
)
:found_ip

REM Step 3: Launch server and browser
echo.
echo [3/3] Starting production server on port 8000...
start "" http://localhost:8000
cd backend
call .venv\Scripts\python.exe main.py

pause
