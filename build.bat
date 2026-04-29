@echo off
REM build.bat — Build Canvas Study Help for Windows
REM Usage: double-click or run from Command Prompt

echo === Canvas Study Help — Build Script ===
echo Platform: Windows

REM 1. Check Python
where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: python not found. Install Python 3.8+ from python.org and try again.
    pause
    exit /b 1
)
python --version

REM 2. Create virtual environment if needed
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)
call .venv\Scripts\activate.bat

REM 3. Install build dependencies
echo Installing PyInstaller...
pip install --quiet --upgrade pip
pip install --quiet pyinstaller

REM 4. Build
echo Building with PyInstaller...
pyinstaller canvas-study.spec --noconfirm

echo.
echo === Build complete! ===
echo Executable: dist\CanvasStudyHelp.exe
echo Tip: copy CanvasStudyHelp.exe anywhere and double-click to run.
pause
