# NovaPad 2.0 – Complete Build & Distribution Guide

This guide takes you from raw source code to a signed, professional Windows
installer (`NovaPad_Setup_2.0.0.exe`) that works on any Windows 10/11 machine
with **no Python or dependencies pre-installed**.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Project Structure](#2-project-structure)
3. [Running from Source](#3-running-from-source)
4. [Build Pipeline Overview](#4-build-pipeline-overview)
5. [Step 1 – Bundling with PyInstaller](#5-step-1--bundling-with-pyinstaller)
6. [Step 2 – Creating the Installer with Inno Setup](#6-step-2--creating-the-installer-with-inno-setup)
7. [One-Command Build](#7-one-command-build)
8. [Custom App Icon (.ico)](#8-custom-app-icon-ico)
9. [Code Signing (Critical for Distribution)](#9-code-signing-critical-for-distribution)
10. [Reducing Antivirus False Positives](#10-reducing-antivirus-false-positives)
11. [PyInstaller vs Nuitka – Decision Guide](#11-pyinstaller-vs-nuitka--decision-guide)
12. [One-File vs One-Folder – Tradeoff Analysis](#12-one-file-vs-one-folder--tradeoff-analysis)
13. [Silent Install & Enterprise Deployment](#13-silent-install--enterprise-deployment)
14. [Troubleshooting](#14-troubleshooting)

---

## 1. Prerequisites

| Tool | Version | Where to get it |
|---|---|---|
| **Python** | 3.10 – 3.12 | https://python.org (check "Add to PATH") |
| **PyInstaller** | ≥ 6.0 | `pip install pyinstaller` |
| **Inno Setup** | 6.x | https://jrsoftware.org/isdl.php |
| **UPX** *(optional)* | latest | https://upx.github.io |
| **PyQt6** | ≥ 6.5 | `pip install PyQt6` |

> **Always build inside a clean virtual environment.** Building from a global
> Python install will bundle every package you ever installed, making the EXE
> gigantic and harder to sign.

---

## 2. Project Structure

```
novapad/
├── main.py                     ← Entry point
├── requirements.txt
├── novapad.spec                ← PyInstaller spec
├── build.bat                   ← One-command build script (Windows)
│
├── assets/
│   ├── __init__.py
│   ├── icons.py                ← SVG icon system (no external files)
│   └── novapad.ico             ← App icon (create this – see §8)
│
├── core/
│   ├── editor.py               ← CodeEditor widget
│   ├── highlighter.py          ← VS Code-style syntax highlighter
│   └── tab_manager.py          ← Multi-tab management
│
├── ui/
│   ├── main_window.py          ← Main window, menus, toolbar
│   ├── find_bar.py             ← Find/Replace panel
│   └── theme.py                ← Light + Dark QSS stylesheets
│
├── utils/
│   └── session.py              ← Session save/restore
│
└── installer/
    ├── novapad_setup.iss       ← Inno Setup script
    └── Output/                 ← Final installer appears here
```

---

## 3. Running from Source

```bash
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # macOS / Linux

# Install dependencies
pip install -r requirements.txt

# Launch NovaPad
python main.py
```

---

## 4. Build Pipeline Overview

```
Source Code (Python)
        │
        ▼
  ┌─────────────┐      Embeds Python runtime, PyQt6 DLLs,
  │ PyInstaller │ ───► Qt plugins, and all .py files into:
  └─────────────┘      dist/NovaPad/  (~80–120 MB folder)
        │
        ▼
  ┌─────────────┐      Compresses the folder, adds an install
  │  Inno Setup │ ───► wizard, shortcuts, registry entries → 
  └─────────────┘      NovaPad_Setup_2.0.0.exe  (~30–50 MB)
        │
        ▼
  Distribute the single .exe installer
  Works on any Windows 10/11 (no Python needed)
```

---

## 5. Step 1 – Bundling with PyInstaller

### A. Set up environment

```bat
cd novapad
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### B. Run PyInstaller

```bat
pyinstaller novapad.spec --noconfirm
```

Or with manual flags (equivalent):

```bat
pyinstaller main.py ^
    --name NovaPad ^
    --noconsole ^
    --noconfirm ^
    --hidden-import PyQt6.QtSvg ^
    --add-data "assets;assets" ^
    --add-data "core;core" ^
    --add-data "ui;ui" ^
    --add-data "utils;utils" ^
    --exclude-module PyQt6.QtWebEngineWidgets ^
    --exclude-module matplotlib ^
    --exclude-module numpy ^
    --exclude-module tkinter
```

### C. Key flags explained

| Flag | Purpose |
|---|---|
| `--noconsole` | No terminal window on launch (essential for GUI apps) |
| `--hidden-import PyQt6.QtSvg` | SVG renderer isn't auto-detected; must be explicit |
| `--add-data "assets;assets"` | Bundle the `assets/` package into the EXE |
| `--exclude-module matplotlib` | Strip unused packages – saves ~20 MB |
| `--noconfirm` | Overwrite previous dist without prompting |

### D. Verify the output

```bat
dist\NovaPad\NovaPad.exe
```

It should launch NovaPad with no console window. Test all features before
proceeding to the installer step.

---

## 6. Step 2 – Creating the Installer with Inno Setup

### A. Install Inno Setup 6

Download from https://jrsoftware.org/isdl.php and run the installer.
The default path is `C:\Program Files (x86)\Inno Setup 6\`.

### B. Compile the installer script

**Option 1 – GUI:**
1. Open Inno Setup Compiler
2. `File → Open` → select `installer/novapad_setup.iss`
3. Press `F9` (Build) or `Build → Compile`

**Option 2 – Command line:**
```bat
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\novapad_setup.iss
```

### C. Output

```
installer\Output\NovaPad_Setup_2.0.0.exe
```

This single EXE is your distributable installer. It:
- Shows a professional wizard UI
- Lets users choose install directory
- Creates Start Menu and optional Desktop shortcuts
- Registers in Add/Remove Programs (Control Panel)
- Includes a proper uninstaller
- Associates `.txt`, `.md`, `.py` with NovaPad (user's choice)

### D. What users see when running the installer

```
Welcome page → License (if included) → Choose Install Dir
→ Select Components → Ready to Install → Installing... → Finish
```

Users can tick "Launch NovaPad" on the final page.

---

## 7. One-Command Build

```bat
build.bat
```

This script:
1. Creates `.venv` if missing
2. Installs all dependencies
3. Runs PyInstaller
4. Runs Inno Setup (if installed)
5. Reports output paths

Individual steps:
```bat
build.bat --pyinstaller    # PyInstaller only
build.bat --inno           # Inno Setup only
build.bat --clean          # Remove all build artefacts
```

---

## 8. Custom App Icon (.ico)

NovaPad's icon system renders SVG at runtime, but the **Windows taskbar and
EXE file icon** require a `.ico` file at build time.

### Creating an .ico file

**Option A – Command line with Pillow:**
```python
from PIL import Image

# If you have a 256x256 PNG:
img = Image.open("assets/novapad_256.png").convert("RGBA")

# Save multi-resolution .ico (16, 24, 32, 48, 64, 128, 256 px)
img.save("assets/novapad.ico", format="ICO",
         sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
```

**Option B – Free online tools:**
- https://convertio.co/png-ico/
- https://icoconvert.com

Include all sizes: 16×16, 32×32, 48×48, 256×256 minimum.

### Applying the icon

In `novapad.spec`, uncomment:
```python
exe = EXE(
    ...
    icon="assets/novapad.ico",   # ← uncomment this line
)
```

In `installer/novapad_setup.iss`, uncomment:
```ini
[Setup]
SetupIconFile=assets\novapad.ico
```

The icon will appear on:
- `NovaPad.exe` (file icon in Explorer)
- The window title bar and taskbar
- The installer EXE
- Add/Remove Programs entry

---

## 9. Code Signing (Critical for Distribution)

**Why this matters:** Windows SmartScreen and antivirus software flag any
unsigned EXE as "unknown publisher" and display a warning ("Windows protected
your PC"). Most users click "Don't run". For serious distribution you must
sign the EXE.

### What you need

1. **A code signing certificate** from a trusted CA:
   - DigiCert (~$300/yr) – industry standard
   - Sectigo (~$200/yr) – popular budget option
   - GlobalSign, Comodo, SSL.com

2. **signtool.exe** – ships with the Windows SDK (free)

### Signing after build

```bat
REM Sign NovaPad.exe
signtool sign ^
    /fd SHA256 ^
    /tr http://timestamp.sectigo.com ^
    /td SHA256 ^
    /f "path\to\your_certificate.pfx" ^
    /p "your_certificate_password" ^
    dist\NovaPad\NovaPad.exe

REM Sign the installer
signtool sign ^
    /fd SHA256 ^
    /tr http://timestamp.sectigo.com ^
    /td SHA256 ^
    /f "path\to\your_certificate.pfx" ^
    /p "your_certificate_password" ^
    installer\Output\NovaPad_Setup_2.0.0.exe
```

### Timestamping

Always timestamp with `/tr` + `/td SHA256`. This ensures the signature
remains valid even after your certificate expires.

### EV vs OV certificates

| Type | Cost | SmartScreen | Use case |
|---|---|---|---|
| **OV** (Organization Validation) | ~$200/yr | Yellow warning for ~1–2 weeks then clears | Individuals/small teams |
| **EV** (Extended Validation) | ~$350/yr | SmartScreen trust immediately | Commercial software |

> **For open-source projects:** Microsoft offers free code signing through
> the Windows Dev Center for listed open-source projects.

---

## 10. Reducing Antivirus False Positives

PyInstaller-packed executables are commonly flagged by antivirus because:
- The bootloader pattern is identical across all PyInstaller apps
- The EXE unpacks Python to a temp directory at runtime
- Unsigned EXEs get extra scrutiny

### Mitigation strategies

1. **Sign the EXE** (most effective – see §9)

2. **Build a fresh PyInstaller bootloader from source:**
   ```bat
   pip install pyinstaller --upgrade
   cd %LOCALAPPDATA%\Programs\Python\Python312\Lib\site-packages\PyInstaller\bootloader
   python waf all
   ```
   A custom-built bootloader has a unique signature that AV heuristics don't
   flag as "known PyInstaller pattern".

3. **Use UPX compression** – changes the binary signature slightly
   ```bat
   pyinstaller novapad.spec  # UPX is enabled in the spec
   ```

4. **Submit for AV whitelisting** – major vendors (Microsoft, Malwarebytes,
   Bitdefender) have online submission portals for false-positive reports.

5. **Consider Nuitka for smaller/cleaner binaries** (see §11)

---

## 11. PyInstaller vs Nuitka – Decision Guide

| Criterion | PyInstaller 6 | Nuitka |
|---|---|---|
| **Compilation** | Bundles Python bytecode as-is | Compiles Python → C → native machine code |
| **Startup speed** | ~0.5–2 s (unzip temp files) | ~0.1–0.3 s (true native binary) |
| **Binary size** | 80–120 MB (folder) | 30–70 MB |
| **AV false positives** | High (known pattern) | Low (looks like a real compiled app) |
| **Build time** | 30–90 s | 5–30 min (compilation) |
| **Ease of use** | Very easy, one command | More setup, `--follow-imports` needed |
| **PyQt6 support** | Excellent, well-tested | Good, requires `--plugin=pyqt6` |
| **Obfuscation** | None (bytecode reversible) | Strong (C compilation) |
| **Best for** | Quick builds, open source | Commercial/distributed apps |

### Nuitka build command for NovaPad

```bat
pip install nuitka ordered-set zstandard

python -m nuitka ^
    --standalone ^
    --onefile ^
    --windows-disable-console ^
    --windows-icon-from-ico=assets/novapad.ico ^
    --plugin-enable=pyqt6 ^
    --include-package=assets ^
    --include-package=core ^
    --include-package=ui ^
    --include-package=utils ^
    --output-filename=NovaPad.exe ^
    main.py
```

**Verdict:** Use PyInstaller for fast iteration during development. Switch to
Nuitka for the final distribution build to reduce size and AV flags.

---

## 12. One-File vs One-Folder – Tradeoff Analysis

| | `--onefile` | `--onedir` (one-folder) |
|---|---|---|
| **Distribution** | Single EXE to share | Entire folder (zip or installer) |
| **Cold startup** | 2–8 s (extracts to %TEMP%) | 0.3–1 s (no extraction) |
| **Warm startup** | 0.5–2 s (cached) | 0.3–1 s |
| **Update deployment** | Replace one file | Replace folder or use installer |
| **Antivirus** | Higher suspicion (extraction) | Lower |
| **Best for** | Portable USB drives | Production installs via installer |

**NovaPad uses one-folder mode** (`COLLECT` in the spec). The Inno Setup
installer wraps this into a single professional `setup.exe` so users still
get a one-click install experience, without the startup penalty.

---

## 13. Silent Install & Enterprise Deployment

Inno Setup supports standard silent install flags:

```bat
# User sees no UI, no prompts
NovaPad_Setup_2.0.0.exe /VERYSILENT /SUPPRESSMSGBOXES

# User sees a progress bar but no wizard pages
NovaPad_Setup_2.0.0.exe /SILENT

# Custom install dir
NovaPad_Setup_2.0.0.exe /VERYSILENT /DIR="D:\Apps\NovaPad"

# Don't create desktop shortcut
NovaPad_Setup_2.0.0.exe /VERYSILENT /TASKS="!desktopicon"

# Log the install to a file
NovaPad_Setup_2.0.0.exe /VERYSILENT /LOG="C:\install_log.txt"
```

These flags make NovaPad deployable via **Group Policy**, **SCCM/Intune**,
or any enterprise software management platform.

---

## 14. Troubleshooting

### "Failed to execute script" on launch
The EXE crashes silently. Build with the console visible to see the traceback:

```bat
pyinstaller main.py --name NovaPad --noconfirm
REM (no --noconsole yet)
```

Run `dist\NovaPad\NovaPad.exe` from a terminal and read the error.

### Missing module at runtime
Add to `hiddenimports` in `novapad.spec`:
```python
hiddenimports=["PyQt6.QtSvg", "PyQt6.sip", "your.missing.module"],
```

### Antivirus quarantines the EXE
1. Build a fresh PyInstaller bootloader (see §10)
2. Sign the binary (see §9)
3. Submit to AV vendor for whitelisting

### Installer says "Another version is installed"
The registry key `HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\NovaPad_is1`
exists. Either uninstall first, or let the Inno Setup upgrade logic handle it
(the `[Code]` section in the `.iss` detects this automatically).

### Qt platform plugin not found
Ensure `qwindows.dll` is NOT in the UPX exclusion exception list if it's
missing from the bundle. Check that `dist\NovaPad\PyQt6\Qt6\plugins\platforms\`
exists and contains `qwindows.dll`.

### Icons look blurry on HiDPI displays
Make sure `novapad.ico` contains the 256×256 size variant. In code, the
`get_app_icon()` function already generates multiple sizes from SVG.

---

## Quick Reference

```
Full build:
    build.bat

PyInstaller only:
    pyinstaller novapad.spec --noconfirm

Inno Setup only:
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\novapad_setup.iss

Silent install:
    NovaPad_Setup_2.0.0.exe /VERYSILENT /SUPPRESSMSGBOXES

Silent uninstall:
    C:\Program Files\NovaPad\unins000.exe /VERYSILENT
```
