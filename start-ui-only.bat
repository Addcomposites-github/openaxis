@echo off
echo ========================================
echo   OpenAxis - Starting UI Only
echo ========================================
echo.

REM Check if Node.js is installed
where node >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Node.js not found. Please install Node.js 18+
    pause
    exit /b 1
)

echo Starting UI Development Server...
cd src\ui

REM Check if node_modules exists
if not exist "node_modules\" (
    echo [INFO] Installing dependencies...
    call npm install
)

echo.
echo Starting Vite dev server...
call npm run dev
