"""
main.py  –  NovaPad entry point  (v4)
======================================
Handles:
  • HiDPI scaling
  • CLI file arguments:  novapad.exe file1.txt file2.py  (each → new tab)
  • Crash detection and recovery prompt
  • Periodic auto-session save (every 30 s)
  • Clean session mark on exit
"""

import os
import sys

VERSION = "3.1.3"  # single source of truth

os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING",        "1")
os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR",      "1")
os.environ.setdefault("QT_SCALE_FACTOR_ROUNDING_POLICY",  "PassThrough")

from PyQt6.QtCore    import QTimer
from PyQt6.QtWidgets import QApplication

from ui.main_window  import MainWindow
from utils.session   import SessionManager


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("NovaPad")
    app.setApplicationVersion(VERSION)
    app.setOrganizationName("NovaPad")
    app.setStyle("Fusion")

    session = SessionManager()

    # ── Crash detection ───────────────────────────────────────────────────
    crashed = session.was_crash()
    session.mark_running()          # lock file created; cleared on clean exit

    window = MainWindow()

    # ── Restore session or prompt after crash ─────────────────────────────
    cli_files = [a for a in sys.argv[1:] if os.path.isfile(a)]

    if cli_files:
        # Command-line files always win – open each in a new tab
        # Close the default empty tab first if it's unmodified
        default_editor = window._tabs.current_editor()
        has_default_empty = (
            default_editor is not None
            and not default_editor.file_path
            and not default_editor.document().isModified()
            and default_editor.toPlainText() == ""
        )
        for path in cli_files:
            window.open_file(path)
        if has_default_empty and window._tabs.count() > 1:
            window._tabs.removeTab(0)

    elif crashed:
        from ui.dialogs import themed_question
        reply = themed_question(
            window,
            "Restore Session",
            "NovaPad did not close cleanly last time.\n\nRestore your previous session?",
            btn_yes="Restore", btn_no="Start Fresh"
        )
        if reply == "Restore":
            # Close the default empty tab before restoring
            default_editor = window._tabs.current_editor()
            session.restore(window)
            if (default_editor and not default_editor.file_path
                    and not default_editor.document().isModified()
                    and default_editor.toPlainText() == ""):
                idx = window._tabs.index_of_editor(default_editor)
                if idx >= 0 and window._tabs.count() > 1:
                    window._tabs.removeTab(idx)
        else:
            session.discard()

    else:
        # Normal start – silently restore previous session
        default_editor = window._tabs.current_editor()
        session.restore(window)
        if (default_editor and not default_editor.file_path
                and not default_editor.document().isModified()
                and default_editor.toPlainText() == ""
                and window._tabs.count() > 1):
            idx = window._tabs.index_of_editor(default_editor)
            if idx >= 0:
                window._tabs.removeTab(idx)

    window.show()

    # ── Check for updates — fully off-thread, no UI blocking ────────────
    import threading as _threading
    from PyQt6.QtCore import QObject, pyqtSignal

    class _UpdateSignal(QObject):
        found = pyqtSignal(str, str)   # (latest_version, download_url)

    _update_sig = _UpdateSignal()
    _update_sig.found.connect(lambda tag, url: _prompt_update(tag, url))

    def _ver(s):
        try:
            return tuple(int(x) for x in s.strip().lstrip("v").split("."))
        except Exception:
            return (0,)

    def _fetch_update_info():
        import urllib.request, json as _json, traceback
        API_URL = "https://api.github.com/repos/Leem-y/novapad/releases/latest"
        print(f"[update] checking... running VERSION={VERSION}")
        try:
            req = urllib.request.Request(API_URL, headers={"User-Agent": "NovaPad"})
            with urllib.request.urlopen(req, timeout=6) as r:
                data = _json.loads(r.read())

            tag    = data.get("tag_name", "").lstrip("v").strip()
            assets = data.get("assets", [])
            url    = next((a["browser_download_url"] for a in assets
                           if a.get("name", "").lower().endswith(".exe")), None)

            print(f"[update] latest tag={tag!r}  url={url!r}")
            print(f"[update] ver compare: {_ver(tag)} <= {_ver(VERSION)} = {_ver(tag) <= _ver(VERSION)}")

            if not tag or not url:
                print("[update] no tag or url, aborting")
                return
            if _ver(tag) <= _ver(VERSION):
                print("[update] already up to date")
                return

            print("[update] newer version found, emitting signal")
            _update_sig.found.emit(tag, url)

        except Exception:
            print(f"[update] EXCEPTION: {traceback.format_exc()}")

    def _prompt_update(latest, install_url):
        from ui.dialogs import themed_update, ThemedProgressDialog, themed_error
        from PyQt6.QtCore import Qt
        import urllib.request, os, tempfile

        msg = (
            f"NovaPad {latest} is available\n\n"
            f"You are on version {VERSION}.\n\n"
            "NovaPad will close, install the update, then relaunch automatically."
        )
        if not themed_update(window, "Update Available", msg):
            return

        prog = ThemedProgressDialog(
            window, "Updating NovaPad",
            f"Downloading NovaPad {latest}...", can_cancel=True
        )
        prog.setWindowModality(Qt.WindowModality.ApplicationModal)
        prog.show()
        QApplication.processEvents()

        tmp_path = os.path.join(
            tempfile.gettempdir(), f"NovaPad_Setup_{latest}.exe"
        )

        _dl_progress = [0]
        _dl_done     = [False]
        _dl_error    = [False]

        def _download():
            try:
                def _hook(count, block, total):
                    if total > 0:
                        _dl_progress[0] = min(99, int(count * block * 100 / total))
                urllib.request.urlretrieve(install_url, tmp_path, _hook)
                _dl_progress[0] = 100
            except Exception:
                _dl_error[0] = True
            finally:
                _dl_done[0] = True

        _threading.Thread(target=_download, daemon=True).start()

        poll = QTimer()
        def _poll():
            if prog.wasCanceled():
                poll.stop()
                return
            prog.setValue(_dl_progress[0])
            if _dl_done[0]:
                poll.stop()
                prog.close()
                if _dl_error[0]:
                    themed_error(window, "Update Failed",
                                 "Could not download the update.\nCheck your internet connection and try again.")
                    return
                _launch_installer(tmp_path, latest)
        poll.timeout.connect(_poll)
        poll.start(100)

    def _launch_installer(tmp_path, latest):
        import subprocess, os, tempfile
        session.save(window)
        session.mark_clean_exit()

        # Write a batch file that:
        #  1. Waits 2s for NovaPad to fully exit
        #  2. Runs the Inno Setup installer (/SILENT = shows progress, no wizard)
        #  3. Finds the new NovaPad.exe via App Paths registry (HKCU first,
        #     then HKLM), falls back to default path
        #  4. Relaunches NovaPad
        launcher = os.path.join(tempfile.gettempdir(), "novapad_updater.bat")
        hkcu_key = r"HKCU\Software\Microsoft\Windows\CurrentVersion\App Paths\NovaPad.exe"
        hklm_key = r"HKLM\Software\Microsoft\Windows\CurrentVersion\App Paths\NovaPad.exe"
        fallback = r"%ProgramFiles%\NovaPad\NovaPad.exe"
        bat = "\n".join([
            "@echo off",
            "timeout /t 2 /nobreak >nul",
            f'start "" /wait "{tmp_path}" /SILENT /SUPPRESSMSGBOXES /NORESTART',
            f'for /f "tokens=2*" %%a in (\'reg query "{hkcu_key}" /ve 2^>nul\') do set NP=%%b',
            "if not defined NP (",
            f'  for /f "tokens=2*" %%a in (\'reg query "{hklm_key}" /ve 2^>nul\') do set NP=%%b',
            ")",
            f"if not defined NP set NP={fallback}",
            'start "" "%NP%"',
            "",
        ])
        with open(launcher, "w", encoding="utf-8") as lf:
            lf.write(bat)

        subprocess.Popen(
            ["cmd.exe", "/c", launcher],
            creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
            close_fds=True,
        )
        window.close()

    # ── TEMP TEST: uncomment to bypass GitHub and test locally ─────────
    # QTimer.singleShot(3000, lambda: _prompt_update(
    #     "3.1.3", r"C:\Python\novapad\installer\Output\NovaPad_Setup_3.1.3.exe"))
    # ─────────────────────────────────────────────────────────────────────
    _threading.Thread(target=_fetch_update_info, daemon=True).start()

    # ── Periodic auto-session save (every 30 s) ───────────────────────────
    auto_timer = QTimer()
    def _auto_save():
        session.save(window)
        window.statusBar().showMessage("  ✓ Auto-saved", 1500)
    auto_timer.timeout.connect(_auto_save)
    auto_timer.start(30_000)

    # ── Store session ref on window for closeEvent access ─────────────────
    window._session = session

    code = app.exec()

    # Clean exit: save session then remove lock file
    session.save(window)
    session.mark_clean_exit()
    sys.exit(code)


if __name__ == "__main__":
    main()
