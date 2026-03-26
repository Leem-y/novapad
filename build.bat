@echo off
REM ═══════════════════════════════════════════════════════════════════
REM  build.bat  –  NovaPad Full Build Pipeline
REM  Produces:  installer\Output\NovaPad_Setup_2.0.0.exe
REM
REM  Requirements (all must be in PATH or configured below):
REM    • Python 3.10+  (with venv module)
REM    • PyInstaller   (installed in venv)
REM    • Inno Setup 6  (default install path or set INNO_PATH below)
REM    • UPX           (optional, set UPX_PATH or leave blank)
REM
REM  Usage:
REM    build.bat                – full build (venv + pyinstaller + inno)
REM    build.bat --pyinstaller  – PyInstaller step only
REM    build.bat --inno         – Inno Setup step only
REM    build.bat --clean        – remove dist/ build/ Output/
REM ═══════════════════════════════════════════════════════════════════

setlocal EnableDelayedExpansion

REM ── Configuration ───────────────────────────────────────────────
set APP_NAME=NovaPad
set APP_VERSION=2.0.0
set VENV_DIR=.venv
set SPEC_FILE=novapad.spec
set ISS_FILE=installer\novapad_setup.iss

REM Inno Setup compiler path (adjust if installed elsewhere)
set "INNO_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist "%INNO_PATH%" (
    set "INNO_PATH=C:\Program Files\Inno Setup 6\ISCC.exe"
)

REM UPX path (leave empty to disable)
set "UPX_PATH=C:\tools\upx\upx.exe"

REM ── Parse arguments ──────────────────────────────────────────────
set DO_PYINSTALLER=1
set DO_INNO=1
set DO_CLEAN=0

if "%1"=="--pyinstaller" (set DO_INNO=0)
if "%1"=="--inno"        (set DO_PYINSTALLER=0)
if "%1"=="--clean"       (set DO_CLEAN=1 & set DO_PYINSTALLER=0 & set DO_INNO=0)

REM ── Clean ────────────────────────────────────────────────────────
if "%DO_CLEAN%"=="1" (
    echo [CLEAN] Removing build artefacts...
    if exist dist\    rmdir /s /q dist
    if exist build\   rmdir /s /q build
    if exist installer\Output\ rmdir /s /q installer\Output
    echo [CLEAN] Done.
    goto :EOF
)

echo.
echo ╔══════════════════════════════════════════════╗
echo ║   NovaPad Build Pipeline  v%APP_VERSION%         ║
echo ╚══════════════════════════════════════════════╝
echo.

REM ── Step 1 – Virtual environment ─────────────────────────────────
if "%DO_PYINSTALLER%"=="1" (
    echo [1/3] Setting up virtual environment...

    if not exist "%VENV_DIR%\Scripts\activate.bat" (
        echo       Creating new venv in %VENV_DIR%\
        python -m venv %VENV_DIR%
        if errorlevel 1 (
            echo [ERROR] Failed to create virtual environment.
            echo         Make sure Python 3.10+ is installed and in PATH.
            exit /b 1
        )
    ) else (
        echo       Found existing venv.
    )

    call %VENV_DIR%\Scripts\activate.bat

    echo       Installing / upgrading dependencies...
    pip install --upgrade pip --quiet
    pip install -r requirements.txt --quiet
    if errorlevel 1 (
        echo [ERROR] pip install failed. Check requirements.txt.
        exit /b 1
    )
    echo       Dependencies OK.
    echo.
)

REM ── Step 2 – PyInstaller bundle ──────────────────────────────────
if "%DO_PYINSTALLER%"=="1" (
    echo [2/3] Running PyInstaller...

    if exist dist\%APP_NAME%\ (
        echo       Removing old dist\%APP_NAME%\ ...
        rmdir /s /q dist\%APP_NAME%
    )

    REM Add UPX to path if available
    if exist "%UPX_PATH%" (
        for %%F in ("%UPX_PATH%") do set "UPX_DIR=%%~dpF"
        set "PATH=%UPX_DIR%;%PATH%"
        echo       UPX found – compression enabled.
    ) else (
        echo       UPX not found – binaries will not be compressed.
    )

    pyinstaller %SPEC_FILE% --noconfirm
    if errorlevel 1 (
        echo [ERROR] PyInstaller failed. See output above.
        exit /b 1
    )

    if not exist "dist\%APP_NAME%\%APP_NAME%.exe" (
        echo [ERROR] Expected dist\%APP_NAME%\%APP_NAME%.exe not found.
        exit /b 1
    )

    echo       PyInstaller OK  –  dist\%APP_NAME%\%APP_NAME%.exe
    echo.
)

REM ── Step 3 – Inno Setup installer ────────────────────────────────
if "%DO_INNO%"=="1" (
    echo [3/3] Running Inno Setup Compiler...

    if not exist "%INNO_PATH%" (
        echo [WARNING] Inno Setup not found at:
        echo           %INNO_PATH%
        echo.
        echo           Download from: https://jrsoftware.org/isdl.php
        echo           Then re-run:   build.bat --inno
        echo.
        echo           PyInstaller output is still usable in dist\%APP_NAME%\
        goto :DONE
    )

    if not exist dist\%APP_NAME%\%APP_NAME%.exe (
        echo [ERROR] dist\%APP_NAME%\%APP_NAME%.exe not found.
        echo         Run PyInstaller first:  build.bat --pyinstaller
        exit /b 1
    )

    mkdir installer\Output 2>nul

    "%INNO_PATH%" %ISS_FILE%
    if errorlevel 1 (
        echo [ERROR] Inno Setup compilation failed.
        exit /b 1
    )

    echo.
    echo       Installer OK  –  installer\Output\%APP_NAME%_Setup_%APP_VERSION%.exe
    echo.
)

:DONE
echo ╔══════════════════════════════════════════════╗
echo ║   BUILD COMPLETE                             ║
echo ╚══════════════════════════════════════════════╝
echo.
echo   App bundle:  dist\%APP_NAME%\%APP_NAME%.exe
echo   Installer:   installer\Output\%APP_NAME%_Setup_%APP_VERSION%.exe
echo.

endlocal
