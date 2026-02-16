@echo off
echo ========================================
echo   OpenAxis - Stopping All Services
echo ========================================
echo.

echo Stopping Python Backend...
taskkill /FI "WindowTitle eq OpenAxis Backend*" /T /F >nul 2>&1

echo Stopping UI Server...
taskkill /FI "WindowTitle eq OpenAxis UI*" /T /F >nul 2>&1

REM Also kill any node/python processes on the ports
echo Killing processes on ports 5173 and 8000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5173') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000') do taskkill /F /PID %%a >nul 2>&1

echo.
echo All services stopped.
echo.
pause
