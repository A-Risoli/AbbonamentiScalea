@echo off
echo ============================================
echo Creating AbbonamentiScalea Installer
echo ============================================
echo.

REM Check if Inno Setup is installed
set "ISCC_PATH=C:\Users\risol\AppData\Local\Programs\Inno Setup 6\ISCC.exe"
if not exist "%ISCC_PATH%" (
    set "ISCC_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
)
if not exist "%ISCC_PATH%" (
    echo ERROR: Inno Setup is not installed!
    echo.
    echo Please download and install from:
    echo https://jrsoftware.org/isdl.php
    echo.
    pause
    exit /b 1
)

REM Check if dist folder exists
if not exist "dist\AbbonamentiScalea" (
    echo ERROR: dist\AbbonamentiScalea folder not found!
    echo.
    echo Please run: python build_installer.py
    echo.
    pause
    exit /b 1
)

echo Building installer with Inno Setup...
echo.

"%ISCC_PATH%" installer.iss

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================
    echo SUCCESS! Installer created!
    echo ============================================
    echo.
    echo Output: installer_output\AbbonamentiScalea-Setup-0.2.0.exe
    echo.
    echo You can now distribute this single installer file.
    echo.
) else (
    echo.
    echo ============================================
    echo ERROR: Build failed!
    echo ============================================
    echo.
)

pause
