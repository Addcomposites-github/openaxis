@echo off
echo ========================================
echo   OpenAxis - First Time Setup
echo ========================================
echo.

REM Check if Python is installed
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python not found. Please install Python 3.10+
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Check if Node.js is installed
where node >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Node.js not found. Please install Node.js 18+
    echo Download from: https://nodejs.org/
    pause
    exit /b 1
)

echo [✓] Python and Node.js found
echo.

REM Setup Python Backend
echo ========================================
echo [1/2] Setting up Python Backend
echo ========================================
cd src\backend

REM Check if virtual environment exists
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing Python dependencies...
pip install --upgrade pip
pip install fastapi uvicorn

echo [✓] Backend setup complete
echo.

REM Setup UI
echo ========================================
echo [2/2] Setting up UI
echo ========================================
cd ..\ui

echo Installing Node.js dependencies...
call npm install

echo [✓] UI setup complete
echo.

REM Copy config files to public if needed
if not exist "public\config\" (
    echo Copying robot config files to public directory...
    mkdir public\config 2>nul
    xcopy /E /I /Y ..\..\config\urdf public\config\urdf >nul
    xcopy /E /I /Y ..\..\config\meshes public\config\meshes >nul
    echo [✓] Config files copied
)

cd ..\..

echo.
echo ========================================
echo   Setup Complete!
echo ========================================
echo.
echo Next steps:
echo   1. Run start.bat to launch OpenAxis
echo   2. Navigate to http://localhost:5173
echo   3. Go to Robot Setup to configure your cell
echo.
echo For development:
echo   - Use start-ui-only.bat to run just the UI
echo   - Use stop.bat to stop all services
echo.
pause
