@echo off
REM Build EntropyGarden Executable
REM Creates a standalone .exe file

echo.
echo ================================================
echo   EntropyGarden Executable Builder
echo ================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    echo Please install Python 3.8+ from https://www.python.org
    pause
    exit /b 1
)

echo [1/3] Installing PyInstaller...
pip install pyinstaller >nul 2>&1

echo.
echo [2/3] Building executable...
echo This may take 30-60 seconds...
echo.

pyinstaller --onefile ^
    --name EntropyGarden ^
    --console ^
    --add-data "entropygarden:entropygarden" ^
    entropygarden/__main__.py

if errorlevel 1 (
    echo ERROR: PyInstaller failed!
    echo Try: pip install --upgrade pyinstaller
    pause
    exit /b 1
)

echo.
echo [3/3] Testing executable...
dist\EntropyGarden.exe --help >nul 2>&1

if errorlevel 1 (
    echo WARNING: Executable created but may have issues.
    echo Try running: dist\EntropyGarden.exe --help
    pause
    exit /b 1
)

echo.
echo ================================================
echo   SUCCESS - Executable created!
echo ================================================
echo.
echo Location: dist\EntropyGarden.exe
echo Size: ~50 MB (includes Python runtime + all dependencies)
echo.
echo Usage:
echo   EntropyGarden.exe grow --input image.ppm --output-private .\keys\priv.key --output-public .\keys\pub.json
echo   EntropyGarden.exe export --key .\keys\priv.key --format json --output .\keys\priv.json
echo   EntropyGarden.exe --help
echo.
echo You can now:
echo - Copy dist\EntropyGarden.exe to any Windows machine
echo - Run it without needing Python installed
echo - Share it with others
echo.
pause
