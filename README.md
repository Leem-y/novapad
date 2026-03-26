# NovaPad

A fast, modern text editor for Windows. Built with PyQt6 — ships as a standalone `.exe`.

---

## Features

### Editor
- **Multi-cursor editing** — `Alt+Click` to place extra cursors, `Ctrl+Alt+↑/↓` to add above/below. All cursors type simultaneously.
- **Syntax highlighting** — Python, JavaScript/TypeScript, HTML/XML, CSS, JSON, Lua
- **Find & Replace** — two-row bar with regex (`.*`), whole word (`\b`), case-sensitive (`Aa`), wrap indicator
- **Auto-indent** — matches indentation of the current line on Enter
- **Bracket/quote auto-close** — `(`, `[`, `{`, `"`, `'` all auto-pair
- **Smart Home** — first press goes to first non-whitespace; second press goes to column 0
- **Line operations** — `Ctrl+D` duplicate, `Ctrl+/` toggle comment, `Alt+↑/↓` move line
- **Select all occurrences** — `Ctrl+Shift+L`
- **Word occurrence highlighting** — highlights all instances of selected text
- **Zoom** — `Ctrl+=` / `Ctrl+-` / `Ctrl+0`
- **Minimap** — VS Code-style document overview (`Ctrl+Shift+M`)
- **Line numbers** — seamless gutter that matches the editor background
- **Bookmarks** — mark and jump to lines
- **Go to line** — `Ctrl+G`

### Tabs
- **Drag to reorder** — animated tab shifting with a floating drag preview
- **Inline rename** — double-click any tab to rename it
- **Session restore** — all open tabs (including unsaved content) are restored on next launch
- **Crash recovery** — detects unclean exits and prompts to restore

### Themes
63 themes — 33 dark, 30 light. Every color in the UI comes from the active theme including the gutter, cursor, tabs, dialogs, and Windows title bar.

**Dark:** NovaPad Dark, VS Code Dark+, One Dark Pro, Monokai, Dracula, Tokyo Night, Tokyo Night Storm, Gruvbox Dark, Nord, Catppuccin Mocha, Catppuccin Macchiato, Catppuccin Frappe, Solarized Dark, Material Dark, Palenight, Ayu Dark, Tomorrow Night, Cobalt2, Night Owl, SynthWave 84, Rose Pine, Rose Pine Moon, Kanagawa Wave, Kanagawa Dragon, Everforest Dark, Horizon Dark, Poimandres, Oxocarbon, Vesper, Moonlight, Melange Dark, Monokai Pro, Bluloco Dark, Rosebox, Flexoki Dark, Mellow, and more

**Light:** NovaPad Light, GitHub Light, Solarized Light, One Light, Tomorrow, Rose Pine Dawn, Catppuccin Latte, Gruvbox Light, Everforest Light, Kanagawa Lotus, Ayu Light, Flexoki Light, Arctic, Mint, Peach, Lavender, Sakura, Fog, Linen, Sandstone, Parchment, Wheat, Copper, Forest Mist, Cobalt Light, Ink, Dusk, and more

Theme switching uses a crossfade transition. Click the paintbrush icon in the toolbar to open the theme picker.

### UI
- **Themed dialogs** — all popups (unsaved changes, update, crash recovery) match the active theme
- **Animated theme transitions** — smooth crossfade when switching themes
- **Focus mode** — `View → Distraction-Free Mode` hides all chrome. Exit via the `Exit Focus` button in the top-right corner
- **Command palette** — `Ctrl+P` fuzzy-searches all menu actions
- **Recent files** — `File → Recent Files` remembers the last 10 opened files
- **Auto-save** — saves all files with paths every 60 seconds
- **Timestamps** — `F5` inserts `YYYY-MM-DD HH:MM:SS` at cursor

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
| `Ctrl+Z` / `Ctrl+Y` | Undo / Redo |
| `Ctrl+F` | Find |
| `Ctrl+H` | Find & Replace |
| `Ctrl+G` | Go to line |
| `Ctrl+P` | Command palette |
| `Ctrl+D` | Duplicate line |
| `Ctrl+/` | Toggle comment |
| `Ctrl+Shift+L` | Select all occurrences |
| `Alt+Up/Down` | Move line up/down |
| `Ctrl+Alt+Up/Down` | Add cursor above/below |
| `Alt+Click` | Add cursor at click position |
| `Escape` | Clear extra cursors |
| `Ctrl+=` / `Ctrl+-` / `Ctrl+0` | Zoom in / out / reset |
| `Alt+Z` | Toggle word wrap |
| `Ctrl+Shift+M` | Toggle minimap |
| `F5` | Insert timestamp |
| `Tab` / `Shift+Tab` | Indent / un-indent |
| `Ctrl+Shift+G` | Toggle line numbers |

---

## Getting Started

**Requirements:** Python 3.10+ and pip.

```bash
git clone https://github.com/Leem-y/novapad
cd novapad
pip install -r requirements.txt
py main.py
```

---

## Building

Run `build.bat` from the project root. Requires PyInstaller and Inno Setup 6.

```bat
build.bat
```

The installer is output to `installer/Output/NovaPad_Setup_x.x.x.exe`.

---

## Project Structure

```
novapad/
├── main.py                 # Entry point
├── build.bat               # One-click build script
├── requirements.txt
├── assets/
│   └── icons.py            # SVG icon definitions (theme-aware)
├── core/
│   ├── editor.py           # CodeEditor — multi-cursor, gutter, highlighting
│   ├── tab_manager.py      # Tab bar with drag reorder and inline rename
│   └── highlighter.py      # Syntax highlighter
├── ui/
│   ├── main_window.py      # Main window, menus, toolbar, status bar
│   ├── theme.py            # 63-theme system with ThemeManager
│   ├── theme_picker.py     # Paintbrush theme picker with swatches + crossfade
│   ├── dialogs.py          # Fully themed replacements for QMessageBox
│   ├── find_bar.py         # Find & Replace bar
│   ├── minimap.py          # Document minimap
│   ├── command_palette.py  # Ctrl+P command palette
│   ├── bookmarks.py        # Bookmark manager
│   └── goto_line.py        # Go to line dialog
└── utils/
    └── session.py          # Session save/restore with crash detection
```

---

## License

MIT — free to use, modify, and distribute.
