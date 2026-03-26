# NovaPad 📝

A modern, high-performance text editor inspired by Notepad++ with a clean macOS/Apple aesthetic. Built with PyQt6 for Windows, macOS, and Linux — compiles to a standalone `.exe` with PyInstaller.

---

## ✨ Features

### Core
| Feature | Details |
|---|---|
| **Tabbed editing** | Open unlimited files in tabs — drag to reorder |
| **New / Open / Save / Save As** | Full file management with keyboard shortcuts |
| **Undo / Redo** | Unlimited undo history per tab |
| **Cut / Copy / Paste / Select All** | Standard clipboard operations |

### Advanced Editor
| Feature | Details |
|---|---|
| **Line numbers** | Auto-updating gutter with current-line highlighting |
| **Syntax highlighting** | Python, JavaScript/TypeScript, HTML/XML, CSS |
| **Current line highlight** | Subtle background tint on cursor line |
| **Word wrap toggle** | `Alt+Z` or View menu |
| **Tab → Spaces** | Tab key inserts 4 spaces; Shift+Tab un-indents |

### Convenience
| Feature | Details |
|---|---|
| **F5 Timestamp** | Inserts `YYYY-MM-DD HH:MM:SS` at cursor |
| **Find & Replace** | `Ctrl+F` / `Ctrl+H` — with match counter, case, wrap-around |
| **Auto-save** | Saves all modified files with paths every 60 seconds |
| **Session restore** | Re-opens your previous files on next launch |
| **Zoom In/Out** | `Ctrl+=` / `Ctrl+-` / `Ctrl+0` |

### Appearance
| Feature | Details |
|---|---|
| **Dark Mode** | `Ctrl+Shift+D` or toolbar moon button |
| **Light Mode** | Clean, minimal Apple-inspired stylesheet |
| **Persistent settings** | Theme, word-wrap, line-numbers persist across sessions |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10 or later
- pip

### Installation

```bash
# 1. Clone or extract NovaPad
cd novapad

# 2. (Optional but recommended) Create a virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run NovaPad
python main.py
```

---

## 🏗️ Building a Standalone Executable (.exe)

### Using PyInstaller (recommended)

```bash
# Install PyInstaller
pip install pyinstaller

# Option A — Use the included spec file (recommended)
pyinstaller novapad.spec

# Option B — Quick single-command build
pyinstaller main.py \
    --noconsole \
    --name NovaPad \
    --noconfirm \
    --exclude-module matplotlib \
    --exclude-module numpy \
    --exclude-module PyQt6.QtWebEngineWidgets
```

The built application will be in `dist/NovaPad/`. Share the entire `NovaPad/` folder or use a tool like [InstallForge](https://installforge.net/) to wrap it into an installer.

### Build Tips
- **Always build on the target OS** — PyInstaller is not a cross-compiler.
- Build inside a **clean virtual environment** to avoid bundling unneeded packages.
- If UPX is installed it will compress the `.exe` further (~30% smaller). Download from https://upx.github.io.
- Add `--icon=assets/icon.ico` to set a custom taskbar icon.

---

## 📁 Project Structure

```
novapad/
├── main.py                  # Entry point — run this
├── requirements.txt         # pip dependencies
├── novapad.spec             # PyInstaller build spec
│
├── core/
│   ├── editor.py            # CodeEditor + LineNumberArea + SyntaxHighlighter
│   └── tab_manager.py       # TabManager — multi-file tab control
│
├── ui/
│   ├── main_window.py       # MainWindow — menus, toolbar, status bar
│   ├── find_bar.py          # FindBar — inline find/replace widget
│   └── theme.py             # ThemeManager — QSS stylesheets (light + dark)
│
└── utils/
    └── session.py           # SessionManager — save/restore open files
```

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+N` | New tab |
| `Ctrl+O` | Open file |
| `Ctrl+S` | Save |
| `Ctrl+Shift+S` | Save As |
| `Ctrl+Alt+S` | Save all |
| `Ctrl+W` | Close tab |
| `Ctrl+Z` | Undo |
| `Ctrl+Y` | Redo |
| `Ctrl+F` | Find |
| `Ctrl+H` | Find & Replace |
| `F5` | Insert timestamp |
| `Ctrl+Shift+D` | Toggle Dark Mode |
| `Alt+Z` | Toggle Word Wrap |
| `Ctrl+Shift+L` | Toggle Line Numbers |
| `Ctrl+=` | Zoom in |
| `Ctrl+-` | Zoom out |
| `Ctrl+0` | Reset zoom |
| `Tab` | Indent (4 spaces) |
| `Shift+Tab` | Un-indent |
| `Ctrl+]` | Indent selected lines |
| `Ctrl+[` | Un-indent selected lines |
| `Ctrl+Shift+U` | UPPERCASE selection |

---

## 🔌 Extending NovaPad

The architecture is deliberately modular:

- **Add a language** — in `core/editor.py`, add a new `elif lang == "...":` block in `SyntaxHighlighter._build_rules()` and update `_detect_language()`.
- **Add a menu action** — call `self._add_action(menu, ...)` in `ui/main_window.py`.
- **Add a theme** — copy the `LIGHT` / `DARK` dictionaries in `ui/theme.py` and add a new `ThemeManager.apply()` path.
- **Plugins** — the `plugins/` directory is reserved for future plugin loading.

---

## 📄 License

MIT — free to use, modify, and distribute.
