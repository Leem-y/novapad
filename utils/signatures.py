from __future__ import annotations

import json
import uuid
from dataclasses import dataclass

from PyQt6.QtCore import QSettings


@dataclass(slots=True)
class SignatureItem:
    id: str
    name: str
    text: str
    hotkey_mods: int  # shift=1, ctrl=2, alt=4
    hotkey_key: str   # "A"-"Z", "0"-"9", "F1"-"F24"
    enabled: bool = True


_KEY = "signatures.items.v1"


def _default_items() -> list[SignatureItem]:
    return [
        SignatureItem(
            id=uuid.uuid4().hex,
            name="Signature",
            text="",
            hotkey_mods=0,
            hotkey_key="",
            enabled=True,
        )
    ]


def load_items(settings: QSettings) -> list[SignatureItem]:
    raw = settings.value(_KEY, "", str) or ""
    if not raw.strip():
        items = _default_items()
        save_items(settings, items)
        return items
    try:
        data = json.loads(raw)
        out: list[SignatureItem] = []
        for d in (data or []):
            if not isinstance(d, dict):
                continue
            out.append(
                SignatureItem(
                    id=str(d.get("id") or uuid.uuid4().hex),
                    name=str(d.get("name") or "Untitled"),
                    text=str(d.get("text") or ""),
                    hotkey_mods=int(d.get("hotkey_mods") or 0),
                    hotkey_key=str(d.get("hotkey_key") or ""),
                    enabled=bool(d.get("enabled", True)),
                )
            )
        return out or _default_items()
    except Exception:
        return _default_items()


def save_items(settings: QSettings, items: list[SignatureItem]) -> None:
    data = [
        {
            "id": it.id,
            "name": it.name,
            "text": it.text,
            "hotkey_mods": int(it.hotkey_mods),
            "hotkey_key": it.hotkey_key,
            "enabled": bool(it.enabled),
        }
        for it in items
    ]
    settings.setValue(_KEY, json.dumps(data, ensure_ascii=False))

