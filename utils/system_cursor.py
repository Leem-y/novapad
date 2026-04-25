from __future__ import annotations

import sys


def _is_windows() -> bool:
    return sys.platform == "win32"


def _qcursor_to_hcursor(qcursor):
    """
    Convert a Qt QCursor (ARGB pixmap) into a Win32 HCURSOR via CreateIconIndirect.
    """
    if not _is_windows():
        return None

    import ctypes
    from ctypes import wintypes

    from PyQt6.QtGui import QImage

    px = qcursor.pixmap()
    if px.isNull():
        return None

    img = px.toImage().convertToFormat(QImage.Format.Format_ARGB32)
    w = img.width()
    h = img.height()

    # Extract raw BGRA bytes (Qt stores ARGB32 as 0xAARRGGBB in memory; in little-endian it's BGRA).
    ptr = img.bits()
    ptr.setsize(img.sizeInBytes())
    data = bytes(ptr)

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ("biSize", wintypes.DWORD),
            ("biWidth", wintypes.LONG),
            ("biHeight", wintypes.LONG),
            ("biPlanes", wintypes.WORD),
            ("biBitCount", wintypes.WORD),
            ("biCompression", wintypes.DWORD),
            ("biSizeImage", wintypes.DWORD),
            ("biXPelsPerMeter", wintypes.LONG),
            ("biYPelsPerMeter", wintypes.LONG),
            ("biClrUsed", wintypes.DWORD),
            ("biClrImportant", wintypes.DWORD),
        ]

    class BITMAPINFO(ctypes.Structure):
        _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]

    class ICONINFO(ctypes.Structure):
        _fields_ = [
            ("fIcon", wintypes.BOOL),
            ("xHotspot", wintypes.DWORD),
            ("yHotspot", wintypes.DWORD),
            ("hbmMask", wintypes.HBITMAP),
            ("hbmColor", wintypes.HBITMAP),
        ]

    BI_RGB = 0
    DIB_RGB_COLORS = 0

    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32

    # Create a top-down 32-bit DIB section.
    bmi = BITMAPINFO()
    bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.bmiHeader.biWidth = w
    bmi.bmiHeader.biHeight = -h  # negative => top-down
    bmi.bmiHeader.biPlanes = 1
    bmi.bmiHeader.biBitCount = 32
    bmi.bmiHeader.biCompression = BI_RGB

    bits_ptr = ctypes.c_void_p()
    hdc = user32.GetDC(None)
    try:
        hbm_color = gdi32.CreateDIBSection(hdc, ctypes.byref(bmi), DIB_RGB_COLORS, ctypes.byref(bits_ptr), None, 0)
    finally:
        user32.ReleaseDC(None, hdc)

    if not hbm_color:
        return None

    # Copy pixels
    ctypes.memmove(bits_ptr, data, min(len(data), w * h * 4))

    # Create an all-zero monochrome mask (required by ICONINFO; ignored for alpha cursors on modern Windows).
    hbm_mask = gdi32.CreateBitmap(w, h, 1, 1, None)

    try:
        # Hotspot (best-effort)
        try:
            hs = qcursor.hotSpot()
            xhs = int(hs.x())
            yhs = int(hs.y())
        except Exception:
            xhs = 0
            yhs = 0

        ii = ICONINFO()
        ii.fIcon = False
        ii.xHotspot = max(0, xhs)
        ii.yHotspot = max(0, yhs)
        ii.hbmMask = hbm_mask
        ii.hbmColor = hbm_color

        hcur = user32.CreateIconIndirect(ctypes.byref(ii))
        return hcur
    finally:
        # Do not delete hbm_color before CreateIconIndirect result is created.
        # After cursor creation, we can free bitmaps.
        try:
            if hbm_mask:
                gdi32.DeleteObject(hbm_mask)
        except Exception:
            pass
        try:
            if hbm_color:
                gdi32.DeleteObject(hbm_color)
        except Exception:
            pass


def enable_novapad_system_cursors(*, accent: str, is_dark: bool) -> bool:
    """
    Replace common Windows system cursors with NovaPad-themed cursors.
    Restorable via disable_novapad_system_cursors().
    """
    if not _is_windows():
        return False

    import ctypes
    from core.editor import make_arrow_cursor, make_ibeam_cursor

    user32 = ctypes.windll.user32

    # Cursor IDs (OCR_*). See WinUser.h.
    OCR_NORMAL = 32512
    OCR_IBEAM = 32513
    OCR_HAND = 32649
    OCR_SIZEALL = 32646
    OCR_SIZENS = 32645
    OCR_SIZEWE = 32644
    OCR_SIZENESW = 32643
    OCR_SIZENWSE = 32642

    arrow = make_arrow_cursor(accent, is_dark)
    ibeam = make_ibeam_cursor(accent, is_dark)
    mapping = {
        OCR_NORMAL: arrow,
        OCR_IBEAM: ibeam,
        # Disable the hand cursor: keep the OS using arrow/I-beam only.
        OCR_HAND: arrow,
        # Resizes: use arrow for a consistent "NovaPad cursor everywhere" feel.
        OCR_SIZEALL: arrow,
        OCR_SIZENS: arrow,
        OCR_SIZEWE: arrow,
        OCR_SIZENESW: arrow,
        OCR_SIZENWSE: arrow,
    }

    ok = True
    for cid, qc in mapping.items():
        hcur = _qcursor_to_hcursor(qc)
        if not hcur:
            ok = False
            continue
        # SetSystemCursor takes ownership of hcur.
        if not user32.SetSystemCursor(hcur, cid):
            ok = False
    return ok


def disable_novapad_system_cursors() -> bool:
    """
    Restore system cursor scheme (resets to user's configured defaults).
    """
    if not _is_windows():
        return False

    import ctypes

    user32 = ctypes.windll.user32
    SPI_SETCURSORS = 0x0057
    return bool(user32.SystemParametersInfoW(SPI_SETCURSORS, 0, None, 0))

