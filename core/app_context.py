from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import QObject, QSettings, pyqtSignal
from PyQt6.QtWidgets import QApplication

from ui.theme import DEFAULT_THEME, ThemeManager
from utils.session import SessionManager


class ThemeService(QObject):
    """
    Small wrapper around ThemeManager that provides a single, app-wide signal
    when themes change.
    """

    theme_changed = pyqtSignal(str, dict, bool)  # (name, tokens, is_dark)

    def __init__(self, app: QApplication, settings: QSettings):
        super().__init__()
        self._app = app
        self._settings = settings
        self._name = self._settings.value("theme", DEFAULT_THEME, str)

    @property
    def name(self) -> str:
        return self._name

    def apply(self, name: str) -> None:
        self._name = name
        ThemeManager.apply(self._app, name)
        self._settings.setValue("theme", name)
        t = ThemeManager.current()
        self.theme_changed.emit(name, t, bool(t.get("is_dark", True)))


@dataclass(slots=True)
class AppContext:
    """
    Shared application services to make dependencies explicit and reduce
    cross-module reach-through.
    """

    app: QApplication
    settings: QSettings
    session: SessionManager
    theme: ThemeService

    @classmethod
    def create_default(cls, app: QApplication) -> "AppContext":
        settings = QSettings("NovaPad", "NovaPad")
        session = SessionManager()
        theme = ThemeService(app, settings)
        return cls(app=app, settings=settings, session=session, theme=theme)

