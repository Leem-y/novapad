from __future__ import annotations

import datetime as _dt
import os
import platform


def _appdata_dir() -> str:
    """
    Return the NovaPad app-data directory, creating it if needed.
    Kept local to avoid importing SessionManager internals.
    """
    if platform.system() == "Windows":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    elif platform.system() == "Darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    d = os.path.join(base, "NovaPad")
    os.makedirs(d, exist_ok=True)
    return d


def daily_notes_dir() -> str:
    d = os.path.join(_appdata_dir(), "Daily Notes")
    os.makedirs(d, exist_ok=True)
    return d


def note_path_for_date(date: _dt.date) -> str:
    name = date.strftime("%Y-%m-%d") + ".txt"
    return os.path.join(daily_notes_dir(), name)


def _new_note_header(date: _dt.date) -> str:
    iso = date.strftime("%Y-%m-%d")
    long_ = date.strftime("%A, %B %d, %Y").replace(" 0", " ")
    return f"{iso}\n{long_}\n\n"


def ensure_note_exists(path: str, date: _dt.date) -> None:
    if os.path.exists(path):
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(_new_note_header(date))


def read_note(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()

