@echo off
echo ================================
echo  AoH2 Diplomacy Fix - EXE Build
echo ================================
echo.

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

echo Installing PyInstaller...
pip install pyinstaller --quiet

echo.
echo Building .exe...
pyinstaller --onefile --name aoh2_diplomacy_fix --console aoh2_diplomacy_fix.py

echo.
if exist dist\aoh2_diplomacy_fix.exe (
    echo [SUCCESS] Build complete!
    echo Output: dist\aoh2_diplomacy_fix.exe
) else (
    echo [ERROR] Build failed. Check output above.
)

pause
