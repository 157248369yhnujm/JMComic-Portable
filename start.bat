@echo off
setlocal enabledelayedexpansion
title JMComic Downloader
cd /d "%~dp0"

echo ========================================
echo   JMComic Downloader
echo ========================================
echo.

REM --- First-run setup: extract Python runtime ---
if not exist "python\python.exe" (
    echo [Setup] Extracting Python runtime...
    powershell -Command "Expand-Archive -LiteralPath '%~dp0python-embed.zip' -DestinationPath '%~dp0python' -Force" >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Failed to extract Python runtime.
        echo Please make sure python-embed.zip exists and PowerShell is installed.
        pause
        exit /b 1
    )

    REM Write updated _pth to enable site-packages
    python\python.exe -c "open(r'python\python312._pth','w').write('python312.zip\n.\nLib\\site-packages\nimport site\n')"
    if errorlevel 1 (
        echo [ERROR] Failed to configure Python runtime.
        pause
        exit /b 1
    )

    echo [Setup] Python runtime ready.
    echo.
)

REM --- First-run setup: install dependencies ---
if not exist "python\Lib\site-packages\flask" (
    echo [Setup] Installing dependencies, please wait...
    python\python.exe -c "import zipfile,os;sp=os.path.join('python','Lib','site-packages');os.makedirs(sp,exist_ok=True);[zipfile.ZipFile(os.path.join('packages',f)).extractall(sp) for f in os.listdir('packages') if f.endswith('.whl')];print('OK')"
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
    echo [Setup] Dependencies installed successfully.
    echo.
)

REM --- Start ---
echo Server: http://127.0.0.1:5000
echo Press Ctrl+C to stop.
echo.

REM Open browser after a short delay to let the server boot
start "" cmd /c "ping -n 3 127.0.0.1 >nul & start http://127.0.0.1:5000"

REM Run the Flask web server
cd web
..\python\python.exe app.py

REM If server exits unexpectedly, keep window open
echo.
echo Server has stopped. Press any key to exit.
pause >nul
