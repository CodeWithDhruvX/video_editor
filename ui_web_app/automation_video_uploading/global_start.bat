@echo off
echo ============================================================
echo   VideoFlow - Global Launcher
echo ============================================================
echo.

:: Hardcoded project path so this file can be moved and executed from anywhere
set "PROJECT_DIR=c:\Users\dhruv\Downloads\Interview_questions\Golang\video-editor\video_editor\ui_web_app\automation_video_uploading"

if not exist "%PROJECT_DIR%" (
    echo [ERROR] Project directory not found at: %PROJECT_DIR%
    echo Please update the PROJECT_DIR variable inside this batch file if you moved the project.
    pause
    exit /b 1
)

echo [1/2] Starting FastAPI backend...
start "VideoFlow Backend" /D "%PROJECT_DIR%\backend" cmd /k "python main.py"

:: Wait a few seconds for backend to initialize
timeout /t 3 /nobreak >nul

echo [2/2] Starting React frontend...
start "VideoFlow Frontend" /D "%PROJECT_DIR%\frontend" cmd /k "npm run dev"

echo.
echo ============================================================
echo   VideoFlow is starting!
echo   Frontend: http://localhost:5173
echo   Backend:  http://localhost:8000
echo ============================================================
echo.

:: Open the frontend in the default browser
timeout /t 3 /nobreak >nul
start http://localhost:5173
