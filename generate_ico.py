"""
generate_ico.py  –  Render novapad.ico from the app_logo SVG.

Produces a multi-resolution ICO (PNG-compressed layers) at:
  16, 24, 32, 40, 48, 64, 128, 256 px

PNG-in-ICO is supported by Windows Vista+ and gives crisp results
at every DPI scaling level.  Run this before PyInstaller.
"""
import struct, sys, os

# Make project imports available when run from the repo root
sys.path.insert(0, os.path.dirname(__file__))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore    import QByteArray, QBuffer
from PyQt6.QtGui     import QPixmap, QPainter
from PyQt6.QtSvg     import QSvgRenderer

_app = QApplication.instance() or QApplication(sys.argv)

# ── Build SVG bytes with fixed fallback colours ───────────────────────────────
_ACCENT   = "#0A84FF"
_ACCENT2  = "#409CFF"
_ACCENT3  = "#80BAFF"
_BG_DARK  = "#111113"
_BG_MID   = "#1C1C2E"
_FG       = "#F2F2F7"

try:
    # Try to use the real theme colours if the app environment is available
    from ui.theme import ThemeManager, DEFAULT_THEME, THEMES
    t       = THEMES[DEFAULT_THEME]
    _ACCENT  = t["accent"]
    from PyQt6.QtGui import QColor as _QC
    a        = _QC(_ACCENT)
    bg       = _QC(t["bg_toolbar"])
    _BG_DARK = bg.darker(140).name()
    _BG_MID  = bg.darker(110).name()
    _ACCENT2 = a.lighter(130).name()
    _ACCENT3 = a.lighter(160).name()
    _FG      = t["fg_primary"]
except Exception:
    pass

from assets.icons import _SVG
_svg_bytes = _SVG["app_logo"].format(
    accent=_ACCENT, accent2=_ACCENT2, accent3=_ACCENT3,
    bg_dark=_BG_DARK, bg_mid=_BG_MID, fg=_FG,
).encode("utf-8")

renderer = QSvgRenderer(QByteArray(_svg_bytes))

# ── Render each size to PNG bytes ─────────────────────────────────────────────
SIZES = [16, 24, 32, 40, 48, 64, 128, 256]
layers = []

for sz in SIZES:
    from PyQt6.QtCore import Qt
    px = QPixmap(sz, sz)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    renderer.render(p)
    p.end()

    buf = QBuffer()
    buf.open(QBuffer.OpenModeFlag.WriteOnly)
    px.save(buf, "PNG")
    buf.close()
    layers.append((sz, bytes(buf.data())))
    print(f"  rendered {sz}×{sz}  ({len(bytes(buf.data()))} bytes PNG)")

# ── Pack into ICO (PNG-in-ICO, RFC-compatible) ────────────────────────────────
def write_ico(layers, path):
    count  = len(layers)
    # ICO header: reserved=0, type=1 (icon), count
    header = struct.pack("<HHH", 0, 1, count)
    dir_size   = count * 16          # 16 bytes per ICONDIRENTRY
    offset     = 6 + dir_size        # first image starts here

    entries    = b""
    image_data = b""

    for w, png in layers:
        h      = w
        w_byte = 0 if w >= 256 else w   # 0 means 256 in the ICO spec
        h_byte = 0 if h >= 256 else h
        size   = len(png)
        entries += struct.pack("<BBBBHHII",
            w_byte, h_byte,   # width, height
            0,                # color count  (0 = true-color / PNG)
            0,                # reserved
            1,                # color planes
            32,               # bits per pixel
            size,             # size of image data
            offset,           # file offset to image data
        )
        image_data += png
        offset     += size

    with open(path, "wb") as f:
        f.write(header + entries + image_data)

out = os.path.join(os.path.dirname(__file__), "assets", "novapad.ico")
write_ico(layers, out)
print(f"\nWrote {out}  ({os.path.getsize(out):,} bytes, {len(layers)} layers)")
