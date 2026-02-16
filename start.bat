@echo off
echo ========================================
echo   OpenAxis - Starting Application
echo ========================================
echo.

REM Check if Python is installed
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

REM Check if Node.js is installed
where node >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Node.js not found. Please install Node.js 18+
    pause
    exit /b 1
)

echo [1/3] Starting Python Backend (FastAPI + uvicorn)...
cd src\backend
start "OpenAxis Backend" cmd /k "python -m uvicorn server:app --host localhost --port 8080 --reload"
timeout /t 3 /nobreak >nul

echo [2/3] Starting UI Development Server...
cd ..\ui
start "OpenAxis UI" cmd /k "npm run dev"
timeout /t 5 /nobreak >nul

echo [3/3] Opening Browser...
timeout /t 3 /nobreak >nul
start http://localhost:5173

echo.
echo ========================================
echo   OpenAxis is running!
echo ========================================
echo.
echo   Backend:  http://localhost:8080
echo   Frontend: http://localhost:5173
echo.
echo   Press Ctrl+C in the command windows to stop
echo.
pause
