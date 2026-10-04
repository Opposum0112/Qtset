"""Desktop wallpaper management adapter.

Discovers image files in the configured `WALLPAPER_DIR` and applies desktop wallpapers
using Qtile's `set-wallpaper` script or the `feh` X11 background setter fallback.
"""

from __future__ import annotations

import os
from pathlib import Path

from qtile_settings.adapters import configuration
from qtile_settings.adapters.commands import run_command

CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "qtile"
SET_WALLPAPER_BIN = CONFIG_DIR / "scripts" / "set-wallpaper"


def get_wallpaper_dir() -> Path:
    settings = configuration.read_settings()
    raw = str(settings.get("WALLPAPER_DIR", "~/Pictures/Wallpapers"))
    return Path(os.path.expanduser(raw)).resolve()


def list_wallpapers(directory: Path | None = None) -> list[Path]:
    target_dir = directory or get_wallpaper_dir()
    if not target_dir.is_dir():
        return []
    valid_exts = {".jpg", ".jpeg", ".png", ".webp"}
    return sorted(
        [p for p in target_dir.iterdir() if p.is_file() and p.suffix.lower() in valid_exts],
        key=lambda p: p.name.lower(),
    )


def set_wallpaper(image_path: Path | str) -> tuple[bool, str]:
    path = Path(image_path).resolve()
    if not path.is_file():
        return False, f"Wallpaper file not found: {path}"

    if SET_WALLPAPER_BIN.is_file() and os.access(SET_WALLPAPER_BIN, os.X_OK):
        result = run_command([str(SET_WALLPAPER_BIN), str(path)], timeout=6.0)
        return result.ok, result.stdout or result.error or f"Set wallpaper: {path.name}"

    # Fallback to feh
    result = run_command(["feh", "--bg-fill", str(path)], timeout=4.0)
    return result.ok, result.stdout or result.error or f"Wallpaper set using feh: {path.name}"
