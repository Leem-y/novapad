@echo off
setlocal EnableExtensions
cd /d "%~dp0"

rem Same interpreter for icon script, pip, and PyInstaller. Avoids "pip install"
rem on 3.12 while "py" defaults to 3.13 ^(No module named PyInstaller^).
rem Override: set PYTHON=C:\path\to\python.exe before running build.bat
set "PYEXE="
set "PYEXTRA="
if defined PYTHON (
    set "PYEXE=%PYTHON%"
    goto py_chosen
)
rem Prefer a Python that already has PyInstaller ^(common: Store 3.12^)
py -3.12 -c "import PyInstaller" 2>nul
if not errorlevel 1 (
    set "PYEXE=py"
    set "PYEXTRA=-3.12"
    goto py_chosen
)
py -3.13 -c "import PyInstaller" 2>nul
if not errorlevel 1 (
    set "PYEXE=py"
    set "PYEXTRA=-3.13"
    goto py_chosen
)
py -c "import PyInstaller" 2>nul
if not errorlevel 1 (
    set "PYEXE=py"
    goto py_chosen
)
python -c "import PyInstaller" 2>nul
if not errorlevel 1 (
    set "PYEXE=python"
    goto py_chosen
)
rem No PyInstaller yet: pick a concrete interpreter for pip install
py -3.12 -c "0" 2>nul
if not errorlevel 1 (
    set "PYEXE=py"
    set "PYEXTRA=-3.12"
    goto py_chosen
)
py -3.13 -c "0" 2>nul
if not errorlevel 1 (
    set "PYEXE=py"
    set "PYEXTRA=-3.13"
    goto py_chosen
)
py -c "0" 2>nul
if not errorlevel 1 (
    set "PYEXE=py"
    goto py_chosen
)
set "PYEXE=python"

:py_chosen
echo Using Python: "%PYEXE%" %PYEXTRA%
echo Cleaning previous build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo Generating multi-resolution icon...
"%PYEXE%" %PYEXTRA% generate_ico.py
if errorlevel 1 (
    echo WARNING: icon generation failed, using existing .ico
    echo.
)

echo Checking PyInstaller...
"%PYEXE%" %PYEXTRA% -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo Installing PyInstaller into this interpreter...
    "%PYEXE%" %PYEXTRA% -m pip install pyinstaller
    if errorlevel 1 (
        echo ERROR: pip could not install PyInstaller. Run manually:
        echo   "%PYEXE%" %PYEXTRA% -m pip install pyinstaller
        echo Or set PYTHON= to a python.exe that already has PyInstaller.
        goto end
    )
)

echo Building exe ^(novapad.spec^)...
"%PYEXE%" %PYEXTRA% -m PyInstaller novapad.spec --noconfirm
if errorlevel 1 (
    echo ERROR: PyInstaller build failed.
    goto end
)

echo Locating Inno Setup compiler...
rem Optional: set INNO_ISCC= to full path, or set ISCC= before running ^(we do not clear a valid one^)
if defined INNO_ISCC (
    if exist "%INNO_ISCC%" (
        set "ISCC=%INNO_ISCC%"
        goto have_iscc
    )
    echo ERROR: INNO_ISCC is set but file not found: "%INNO_ISCC%"
    goto end
)
if not defined INNO_ISCC if defined ISCC if exist "%ISCC%" goto have_iscc
set "ISCC="
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles(x86)%\Inno Setup 5\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 5\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 5\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 5\ISCC.exe"
if not defined ISCC (
    for /f "usebackq delims=" %%i in (`where ISCC.exe 2^>nul`) do (
        set "ISCC=%%i"
        goto have_iscc
    )
)
:have_iscc
if not defined ISCC (
    echo WARNING: Inno Setup ^(ISCC.exe^) not found - skipping installer step.
    echo The app was still built. Portable folder: dist\NovaPad\
    echo To build the .exe setup: install Inno Setup, then re-run this script.
    echo   winget install JRSoftware.InnoSetup
    echo After install, ISCC is usually in %%LOCALAPPDATA%%\Programs\Inno Setup 6\
    goto end
)

echo Building installer...
"%ISCC%" installer\novapad_setup.iss
if errorlevel 1 (
    echo ERROR: Inno Setup compile failed.
    goto end
)

echo Installer output: installer\Output\

:end
echo.
echo Done.
pause
endlocal
