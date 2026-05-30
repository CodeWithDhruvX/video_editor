@echo off
echo ============================================================
echo   VideoFlow - Automation Video Editor ^& YouTube Uploader
echo ============================================================
echo.

:: Kill existing Python and Node processes to free up ports (8000 and 5173)
echo [0/4] Cleaning up old processes...
taskkill /F /IM python.exe /T >nul 2>&1
taskkill /F /IM node.exe /T >nul 2>&1
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.9+
    pause
    exit /b 1
)

:: Check Node
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found. Please install Node.js 18+
    pause
    exit /b 1
)

:: Install backend dependencies
echo [1/4] Installing Python backend dependencies...
cd /d "%~dp0backend"
pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install Python dependencies
    pause
    exit /b 1
)

:: Install frontend dependencies
echo [2/4] Installing frontend dependencies...
cd /d "%~dp0frontend"
if not exist "node_modules" (
    npm install --silent
)

:: Start backend
echo [3/4] Starting FastAPI backend on http://localhost:8000 ...
cd /d "%~dp0backend"
start "VideoFlow Backend" cmd /k "python main.py"

:: Wait for backend to start
timeout /t 3 /nobreak >nul

:: Start frontend
echo [4/4] Starting React frontend on http://localhost:5173 ...
cd /d "%~dp0frontend"
start "VideoFlow Frontend" cmd /k "npm run dev"

echo.
echo ============================================================
echo   VideoFlow is starting!
echo   Frontend: http://localhost:5173
echo   Backend:  http://localhost:8000
echo   API Docs: http://localhost:8000/docs
echo ============================================================
echo.
timeout /t 3 /nobreak >nul
start http://localhost:5173
