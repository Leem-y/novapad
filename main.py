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

os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING",        "1")
os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR",      "1")
os.environ.setdefault("QT_SCALE_FACTOR_ROUNDING_POLICY",  "PassThrough")

from PyQt6.QtCore    import QTimer
from PyQt6.QtWidgets import QApplication, QMessageBox

from ui.main_window  import MainWindow
from utils.session   import SessionManager


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("NovaPad")
    app.setApplicationVersion("3.0.0")
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
        reply = QMessageBox.question(
            window,
            "Restore Session",
            "NovaPad did not close cleanly last time.\n\n"
            "Restore your previous session?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply == QMessageBox.StandardButton.Yes:
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

    # ── Check for updates (non-blocking, runs 3s after launch) ───────────
    def _check_updates():
        import urllib.request, json
        try:
            url = "https://api.github.com/repos/Leem-y/novapad/releases/latest"
            req = urllib.request.Request(url, headers={"User-Agent": "NovaPad"})
            with urllib.request.urlopen(req, timeout=4) as r:
                data = json.loads(r.read())
            latest  = data.get("tag_name", "").lstrip("v")
            current = "3.0.0"
            if latest and latest != current:
                from PyQt6.QtWidgets import QMessageBox, QPushButton
                msg = QMessageBox(window)
                msg.setWindowTitle("Update Available")
                msg.setText(
                    f"NovaPad {latest} is available!\n\n"
                    f"You are running version {current}.\n"
                    f"Download the latest installer from GitHub."
                )
                msg.setIcon(QMessageBox.Icon.Information)
                open_btn = msg.addButton("Open GitHub", QMessageBox.ButtonRole.AcceptRole)
                msg.addButton("Later", QMessageBox.ButtonRole.RejectRole)
                msg.exec()
                if msg.clickedButton() == open_btn:
                    import webbrowser
                    webbrowser.open("https://github.com/Leem-y/novapad/releases/latest")
        except Exception:
            pass  # silently fail if offline or rate-limited

    update_timer = QTimer()
    update_timer.setSingleShot(True)
    update_timer.timeout.connect(_check_updates)
    update_timer.start(3000)   # 3 seconds after launch

    # ── Periodic auto-session save (every 30 s) ───────────────────────────
    auto_timer = QTimer()
    auto_timer.timeout.connect(lambda: session.save(window))
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
