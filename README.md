# NovaPad

A modern, high-performance text editor built with PyQt6 for Windows. Clean design, rich features, compiles to a standalone `.exe` with PyInstaller.

---

## Features

### Editor
| Feature | Details |
|---|---|
| **Tabbed editing** | Unlimited tabs — drag to reorder, browser-style dynamic width |
| **Syntax highlighting** | Python, JavaScript/TypeScript, HTML/XML, CSS, JSON |
| **Line numbers** | Auto-updating gutter with current-line highlight |
| **Find & Replace** | `Ctrl+F` / `Ctrl+H` — live match highlighting, match counter, case, wrap |
| **Word wrap** | `Alt+Z` or View menu |
| **Zoom** | `Ctrl+=` / `Ctrl+-` / `Ctrl+0` |
| **Smart indent** | Tab inserts 4 spaces; `Shift+Tab` / `Ctrl+]` / `Ctrl+[` indent/un-indent |
| **Duplicate line** | `Ctrl+D` |
| **Toggle comment** | `Ctrl+/` |
| **Smart Home** | First press → first non-whitespace; second press → column 0 |
| **Go to Line** | `Ctrl+G` |

### Timestamps
| Feature | Details |
|---|---|
| **F5 timestamp** | Inserts a styled, read-only date/time line |
| **Protected lines** | Timestamp lines can't be accidentally edited — Backspace deletes the whole line |
| **Theme-aware** | Timestamp color and size always match the active theme |
| **Session-safe** | Timestamps survive autosave and session restore |

### Session & Recovery
| Feature | Details |
|---|---|
| **Session restore** | Silently re-opens all previous tabs on launch |
| **Crash recovery** | Detects unclean exits — prompts to restore or start fresh |
| **Content autosave** | Saves 800 ms after any keystroke, plus a 30-second fallback |
| **Unsaved content** | Unsaved tabs written to temp storage and fully restored |

### Appearance
| Feature | Details |
|---|---|
| **78 themes** | 38 dark, 30 light, 10 gradient — see full list below |
| **Theme picker** | Live-preview overlay when browsing themes |
| **Animated transitions** | Cross-fade when switching themes |
| **Windows 11 title bar** | Title bar colour matched to the active theme via DWM |
| **Gradient themes** | Real `qlineargradient` toolbar — tabs and editor stay clean |
| **Persistent settings** | Theme, word-wrap, line-numbers persist across sessions |

### Tools
| Feature | Details |
|---|---|
| **Minimap** | Live scaled document preview with viewport indicator |
| **Command palette** | `Ctrl+P` — fuzzy-search access to all actions |
| **Format toolbar** | Bold, Italic, Underline, font family and size |
| **Bookmarks** | Toggle, navigate, and clear bookmarks |
| **Auto-update** | Background GitHub release check — one-click download and silent reinstall |

---

## Themes

**Dark** — NovaPad Dark, VS Code Dark+, One Dark Pro, Monokai, Dracula, Tokyo Night, Tokyo Night Storm, Gruvbox Dark, Nord, Catppuccin Mocha, Catppuccin Macchiato, Catppuccin Frappe, Solarized Dark, Material Dark, Palenight, Ayu Dark, Tomorrow Night, Cobalt2, Night Owl, SynthWave 84, Rose Pine, Rose Pine Moon, Kanagawa Wave, Kanagawa Dragon, Everforest Dark, Horizon Dark, Poimandres, Oxocarbon, Vesper, Moonlight, Melange Dark, Monokai Pro, Bluloco Dark, Rosebox, Flexoki Dark, Mellow, Sunset, Aurora, Neon City, Deep Ocean, Midnight Bloom

**Light** — NovaPad Light, GitHub Light, One Light, Tomorrow, Rose Pine Dawn, Catppuccin Latte, Gruvbox Light, Solarized Light, Ayu Light, Everforest Light, Kanagawa Lotus, Flexoki Light, Arctic, Mint, Peach, Lavender, Sakura, Fog, Linen, Sandstone, Parchment, Wheat, Copper, Forest Mist, Cobalt Light, Ink, Dusk, Candy, Tropical Sunrise, Sky Gradient, Rose Gold, Citrus

---

## Quick Start

```bash
# Clone or extract NovaPad
cd novapad

# Create a virtual environment (recommended)
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # macOS / Linux

# Install dependencies
pip install -r requirements.txt

# Run
python main.py
```

---

## Building a Standalone .exe

```bash
pip install pyinstaller

# Recommended — use the included spec file
pyinstaller novapad.spec

# Or quick build
pyinstaller main.py --noconsole --name NovaPad --noconfirm
```

Output is in `dist/NovaPad/`. Use `installer/novapad_setup.iss` with [Inno Setup 6](https://jrsoftware.org/isinfo.php) to produce the installer.

**Tips**
- Build on the target OS — PyInstaller is not a cross-compiler.
- Build inside a clean virtual environment.
- Add `--icon=assets/novapad.ico` for the taskbar icon.

---

## Project Structure

```
novapad/
├── main.py                  # Entry point
├── requirements.txt
├── novapad.spec             # PyInstaller spec
│
├── core/
│   ├── editor.py            # CodeEditor, LineNumberArea, SyntaxHighlighter
│   └── tab_manager.py       # NovaPadTabBar, TabManager
│
├── ui/
│   ├── main_window.py       # MainWindow — menus, toolbar, status bar
│   ├── find_bar.py          # Inline find/replace
│   ├── minimap.py           # Minimap panel
│   ├── theme.py             # ThemeManager — 78 themes + gradient QSS
│   ├── theme_picker.py      # Live-preview theme picker overlay
│   ├── format_toolbar.py    # Rich text format toolbar
│   ├── command_palette.py   # Fuzzy command palette
│   ├── goto_line.py         # Go to Line bar
│   ├── bookmarks.py         # Bookmark manager
│   └── dialogs.py           # Themed dialog helpers
│
├── utils/
│   └── session.py           # SessionManager — save/restore/crash recovery
│
└── installer/
    └── novapad_setup.iss    # Inno Setup 6 installer script
```

---

## Keyboard Shortcuts

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
| `Ctrl+G` | Go to Line |
| `Ctrl+P` | Command palette |
| `Ctrl+D` | Duplicate line |
| `Ctrl+/` | Toggle comment |
| `Ctrl+]` | Indent selection |
| `Ctrl+[` | Un-indent selection |
| `Ctrl+Shift+U` | UPPERCASE selection |
| `F5` | Insert timestamp |
| `Alt+Z` | Toggle word wrap |
| `Ctrl+Shift+L` | Toggle line numbers |
| `Ctrl+=` | Zoom in |
| `Ctrl+-` | Zoom out |
| `Ctrl+0` | Reset zoom |
| `Ctrl+Shift+D` | Toggle dark mode |
| `F1` | About |

---

## License

MIT — free to use, modify, and distribute.
