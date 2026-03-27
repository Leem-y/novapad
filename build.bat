@echo off
D:
cd D:\Python\novapad
echo Cleaning previous build...
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
echo Generating multi-resolution icon...
py generate_ico.py
if errorlevel 1 (echo WARNING: icon generation failed, using existing .ico & echo.)
echo Building exe...
py -m PyInstaller main.py --noconfirm --noconsole --onedir --name NovaPad --hidden-import PyQt6.QtSvg --icon assets\novapad.ico --add-data "assets;assets"

echo Building installer...
set ISCC=
for %%p in ("%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" "%ProgramFiles%\Inno Setup 6\ISCC.exe") do (
    if exist %%p set ISCC=%%p
)
if not defined ISCC (
    echo ERROR: Inno Setup not found. Install with: winget install JRSoftware.InnoSetup
    goto end
)
%ISCC% installer\novapad_setup.iss

:end
echo.
echo Done! Installer is at installer\Output\
pause
