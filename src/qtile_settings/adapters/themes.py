"""Theme discovery and global desktop palette adapter.

Discovers theme JSON definition files in `~/.config/qtile/themes/`, tracks the active
theme preset via `current_theme.json`, and coordinates synchronized application across
the Qtile bar, terminals, and editors via `apply-global-theme`.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from qtile_settings.adapters.commands import run_command

CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "qtile"
THEMES_DIR = CONFIG_DIR / "themes"
CURRENT_THEME_FILE = THEMES_DIR / "current_theme.json"
SCRIPTS_DIR = CONFIG_DIR / "scripts"
APPLY_THEME_BIN = SCRIPTS_DIR / "apply-global-theme"

DEFAULT_PALETTE: dict[str, str] = {
    "base": "#1e1e2e",
    "mantle": "#181825",
    "crust": "#11111b",
    "surface0": "#313244",
    "surface1": "#45475a",
    "surface2": "#585b70",
    "text": "#cdd6f4",
    "subtext": "#a6adc8",
    "overlay": "#6c7086",
    "blue": "#89b4fa",
    "lavender": "#b4befe",
    "green": "#a6e3a1",
    "yellow": "#f9e2af",
    "red": "#f38ba8",
    "mauve": "#cba6f7",
    "peach": "#fab387",
    "teal": "#94e2d5",
}


def list_themes() -> list[str]:
    """Return available theme names found in the themes directory."""
    themes: list[str] = []
    if THEMES_DIR.is_dir():
        for file in sorted(THEMES_DIR.glob("*.json")):
            if file.name != "current_theme.json":
                themes.append(file.stem)
    if not themes:
        # Fallback presets
        themes = [
            "catppuccin-mocha",
            "catppuccin-frappe",
            "catppuccin-latte",
            "gruvbox-dark",
            "github-dark",
            "ayu-dark",
            "solarized-dark",
        ]
    return themes


def get_current_theme_name() -> str:
    """Read the current theme name from current_theme.json."""
    if CURRENT_THEME_FILE.is_file():
        try:
            data = json.loads(CURRENT_THEME_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "name" in data:
                raw_name = str(data["name"])
                # Match against known theme names (case-insensitive and hyphen-tolerant)
                for t in list_themes():
                    if (
                        t.lower() == raw_name.lower()
                        or t.replace("-", " ").lower() == raw_name.lower()
                        or t.lower() == raw_name.replace(" ", "-").lower()
                    ):
                        return t
                return raw_name
        except (OSError, json.JSONDecodeError):
            pass
    return "catppuccin-mocha"


def get_current_theme_palette() -> dict[str, str]:
    """Read active palette directly from current_theme.json, falling back to named palette."""
    if CURRENT_THEME_FILE.is_file():
        try:
            data = json.loads(CURRENT_THEME_FILE.read_text(encoding="utf-8"))
            colors = data.get("colors") or data.get("palette") or {}
            if isinstance(colors, dict) and colors:
                merged = dict(DEFAULT_PALETTE)
                merged.update({k: str(v) for k, v in colors.items()})
                return merged
        except (OSError, json.JSONDecodeError):
            pass
    return get_theme_palette(get_current_theme_name())


def get_theme_palette(theme_name: str) -> dict[str, str]:
    """Load colors dictionary for a given theme name."""
    target = THEMES_DIR / f"{theme_name}.json"
    if target.is_file():
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
            colors = data.get("colors") or data.get("palette") or {}
            if isinstance(colors, dict):
                merged = dict(DEFAULT_PALETTE)
                merged.update({k: str(v) for k, v in colors.items()})
                return merged
        except (OSError, json.JSONDecodeError):
            pass
    return dict(DEFAULT_PALETTE)


def apply_theme(theme_name: str) -> tuple[bool, str]:
    """Apply theme using Qtile-Con's apply-global-theme script, or sync json directly."""
    if APPLY_THEME_BIN.is_file() and os.access(APPLY_THEME_BIN, os.X_OK):
        result = run_command([str(APPLY_THEME_BIN), theme_name], timeout=8.0)
        return result.ok, result.stdout or result.error or f"Applied {theme_name} successfully."

    # Direct fallback if script is not executable: update current_theme.json
    theme_file = THEMES_DIR / f"{theme_name}.json"
    if theme_file.is_file():
        try:
            data = json.loads(theme_file.read_text(encoding="utf-8"))
            CURRENT_THEME_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
            return True, f"Theme set to {theme_name} (current_theme.json updated)."
        except (OSError, json.JSONDecodeError) as exc:
            return False, f"Failed writing theme: {exc}"
    return False, f"Theme file not found: {theme_file}"
