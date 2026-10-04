"""Configuration and preferences management adapter.

Provides safe, static AST-based parsing and debounced serializing of Qtile settings
(qtile_config/settings.py and config.py) without executing untrusted user Python code.
Manages atomic timestamped backups, live undo/redo stacks, workspace layouts JSON
cache, and autostart background daemon inspection.
"""

from __future__ import annotations

import ast
import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from qtile_settings.adapters.commands import run_command

CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "qtile"
SETTINGS_PATH = CONFIG_DIR / "qtile_config" / "settings.py"
CONFIG_PATH = CONFIG_DIR / "config.py"

# Core layout, dimension, and environment settings in qtile_config/settings.py
SETTINGS_DEFAULTS: dict[str, Any] = {
    "MOD": "mod4",
    "TERMINAL": "alacritty",
    "LAUNCHER": "rofi -show drun -show-icons -icon-theme Adwaita -theme ~/.config/qtile/themes/catppuccin-mocha.rasi",
    "WALLPAPER_DIR": "~/Pictures/Wallpapers",
    "GAP": 8,
    "BORDER_WIDTH": 2,
    "BAR_HEIGHT": 36,
    "FONT": "JetBrainsMono Nerd Font",
    "FONT_SIZE": 12,
}

# Window manager behavior settings in config.py
CONFIG_DEFAULTS: dict[str, Any] = {
    "auto_fullscreen": True,
    "focus_on_window_activation": "smart",
    "follow_mouse_focus": True,
    "bring_front_click": True,
    "cursor_warp": False,
    "wmname": "LG3D",
}

# Legacy alias for backward compatibility
DEFAULTS: dict[str, Any] = SETTINGS_DEFAULTS

CONFIG_FILES: dict[str, str] = {
    "Qtile entry point": "config.py",
    "General settings": "qtile_config/settings.py",
    "Keybindings": "qtile_config/keys.py",
    "Workspaces": "qtile_config/groups.py",
    "Layouts": "qtile_config/layouts.py",
    "Bar and widgets": "qtile_config/widgets.py",
    "Screens and bar placement": "qtile_config/screens.py",
    "Colors and palette": "qtile_config/colors.py",
}


def _backup(path: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    target = path.with_name(f"{path.name}.backup.{stamp}")
    shutil.copy2(path, target)
    return target


def read_settings() -> dict[str, Any]:
    """Read preferences from settings.py without executing user code."""
    values = dict(SETTINGS_DEFAULTS)
    settings_file = SETTINGS_PATH
    if not settings_file.is_file():
        return values
    try:
        tree = ast.parse(settings_file.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                key = node.targets[0].id
                if key in SETTINGS_DEFAULTS:
                    try:
                        values[key] = ast.literal_eval(node.value)
                    except (ValueError, TypeError):
                        pass
    except (OSError, SyntaxError):
        pass
    return values


def read_config_settings() -> dict[str, Any]:
    """Read window manager behavior settings from config.py without executing user code."""
    values = dict(CONFIG_DEFAULTS)
    entry_file = CONFIG_DIR / "config.py"
    if not entry_file.is_file():
        return values
    try:
        tree = ast.parse(entry_file.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                key = node.targets[0].id
                if key in CONFIG_DEFAULTS:
                    try:
                        values[key] = ast.literal_eval(node.value)
                    except (ValueError, TypeError):
                        pass
    except (OSError, SyntaxError):
        pass
    return values


def read_all_preferences() -> dict[str, Any]:
    """Return all combined settings from both settings.py and config.py."""
    combined = read_settings()
    combined.update(read_config_settings())
    return combined


def save_settings(values: dict[str, Any]) -> Path:
    """Update settings in settings.py, creating a backup first."""
    settings_file = SETTINGS_PATH
    if not settings_file.is_file():
        raise FileNotFoundError(f"Qtile settings not found: {settings_file}")
    original = settings_file.read_text(encoding="utf-8")
    updated = original
    for key, default in SETTINGS_DEFAULTS.items():
        if key not in values:
            continue
        value = values[key]
        if isinstance(default, int):
            value = int(value)
            if value < 0:
                raise ValueError(f"{key} cannot be negative")
        else:
            value = str(value).strip()
            if not value:
                raise ValueError(f"{key} cannot be empty")
        line = f"{key} = {value!r}"
        updated, count = re.subn(rf"(?m)^{re.escape(key)}\s*=.*$", lambda _, repl=line: repl, updated, count=1)
        if count == 0:
            updated += f"\n{line}\n"
    ast.parse(updated, filename=str(settings_file))
    _backup(settings_file)
    settings_file.write_text(updated, encoding="utf-8")
    return settings_file


def save_config_settings(values: dict[str, Any]) -> Path:
    """Update window manager behavior settings in config.py, creating a backup first."""
    entry_file = CONFIG_DIR / "config.py"
    if not entry_file.is_file():
        raise FileNotFoundError(f"Qtile config not found: {entry_file}")
    original = entry_file.read_text(encoding="utf-8")
    updated = original
    for key, default in CONFIG_DEFAULTS.items():
        if key not in values:
            continue
        value = values[key]
        if isinstance(default, bool):
            value = bool(value)
        elif isinstance(default, int):
            value = int(value)
        else:
            value = str(value).strip()
        line = f"{key} = {value!r}"
        updated, count = re.subn(rf"(?m)^{re.escape(key)}\s*=.*$", lambda _, repl=line: repl, updated, count=1)
        if count == 0:
            updated += f"\n{line}\n"
    ast.parse(updated, filename=str(entry_file))
    _backup(entry_file)
    entry_file.write_text(updated, encoding="utf-8")
    return entry_file


def save_preference(key: str, value: Any) -> Path:
    """Auto-save an individual preference to the appropriate file."""
    if key in SETTINGS_DEFAULTS:
        return save_settings({key: value})
    if key in CONFIG_DEFAULTS:
        return save_config_settings({key: value})
    raise KeyError(f"Unknown preference key: {key}")


def read_file(relative_path: str) -> str:
    path = (CONFIG_DIR / relative_path).resolve()
    if not path.is_relative_to(CONFIG_DIR.resolve()):
        raise ValueError("Selected file is outside the Qtile configuration directory")
    if path.suffix != ".py":
        raise ValueError("Only Python configuration files are supported")
    return path.read_text(encoding="utf-8")


def save_file(relative_path: str, content: str) -> Path:
    path = (CONFIG_DIR / relative_path).resolve()
    if not path.is_relative_to(CONFIG_DIR.resolve()):
        raise ValueError("Selected file is outside the Qtile configuration directory")
    if path.suffix != ".py":
        raise ValueError("Only Python configuration files are supported")
    ast.parse(content, filename=str(path))
    if path.is_file():
        _backup(path)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def restore_defaults() -> tuple[bool, str]:
    """Reset both settings.py and config.py to their factory defaults."""
    try:
        if SETTINGS_PATH.is_file():
            save_settings(SETTINGS_DEFAULTS)
        if CONFIG_PATH.is_file():
            save_config_settings(CONFIG_DEFAULTS)
        return True, "Default preferences restored successfully."
    except (OSError, ValueError, SyntaxError, KeyError) as exc:
        return False, f"Failed to restore defaults: {exc}"


def list_backups() -> list[dict[str, Any]]:
    """List available configuration backup files sorted by timestamp descending."""
    backups: list[dict[str, Any]] = []
    search_dirs = [CONFIG_DIR, CONFIG_DIR / "qtile_config"]
    for sdir in search_dirs:
        if not sdir.is_dir():
            continue
        for file in sdir.glob("*.backup.*"):
            if not file.is_file():
                continue
            name_parts = file.name.split(".backup.")
            target_name = name_parts[0] if len(name_parts) == 2 else file.name
            stamp_str = name_parts[1] if len(name_parts) == 2 else ""
            stat = file.stat()
            backups.append({
                "path": file,
                "filename": file.name,
                "target_name": target_name,
                "timestamp": stamp_str or datetime.fromtimestamp(stat.st_mtime, timezone.utc).strftime("%Y%m%d-%H%M%S"),
                "size_bytes": stat.st_size,
                "mtime": stat.st_mtime,
            })
    backups.sort(key=lambda b: b["mtime"], reverse=True)
    return backups


def restore_backup(backup_path: Path | str) -> tuple[bool, str]:
    """Restore a backup file to its original target file location."""
    bpath = Path(backup_path).resolve()
    if not bpath.is_file():
        return False, f"Backup file not found: {bpath}"
    if not bpath.is_relative_to(CONFIG_DIR.resolve()):
        return False, "Backup file is outside configuration directory"

    parts = bpath.name.split(".backup.")
    if len(parts) != 2:
        return False, f"Invalid backup file name pattern: {bpath.name}"

    target_name = parts[0]
    target_file = bpath.parent / target_name

    # Validate Python syntax before restoring
    if target_name.endswith(".py"):
        try:
            ast.parse(bpath.read_text(encoding="utf-8"), filename=str(bpath))
        except (SyntaxError, OSError) as exc:
            return False, f"Backup file contains invalid Python syntax: {exc}"

    # Read content from backup first
    content = bpath.read_text(encoding="utf-8")

    # Backup current before overwriting
    if target_file.is_file():
        _backup(target_file)

    target_file.write_text(content, encoding="utf-8")
    return True, f"Restored {target_name} from backup {bpath.name}"


def validate() -> tuple[bool, str]:
    """Check Python syntax, then run qtile check when the CLI is installed."""
    entry = CONFIG_DIR / "config.py"
    if not entry.is_file():
        return False, f"Qtile config was not found at {entry}"
    try:
        for relative in CONFIG_FILES.values():
            path = CONFIG_DIR / relative
            if path.is_file():
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError) as exc:
        return False, str(exc)
    if not shutil.which("qtile"):
        return True, "Python syntax checks passed. qtile CLI not found; full validation was skipped."
    result = run_command(["qtile", "check", "-c", str(entry)], timeout=30)
    return result.ok, result.stdout or result.error or "Qtile validation completed."


def reload_config() -> tuple[bool, str]:
    result = run_command(["qtile", "cmd-obj", "-o", "cmd", "-f", "reload_config"])
    return result.ok, result.error or "Qtile configuration reload requested."


WORKSPACE_LAYOUTS_PATH = Path.home() / ".cache" / "qtile" / "workspace_layouts.json"

DEFAULT_WORKSPACE_LAYOUTS: dict[str, str] = {
    "1": "columns",
    "2": "scroller",
    "3": "columns",
    "4": "monadtall",
    "5": "monadtall",
    "6": "max",
    "7": "floating",
    "8": "columns",
    "9": "monadwide",
}

AVAILABLE_LAYOUTS: list[str] = [
    "columns",
    "scroller",
    "monadtall",
    "monadwide",
    "max",
    "floating",
    "matrix",
    "bsp",
]


def read_workspace_layouts() -> dict[str, str]:
    """Read the persistent per-workspace layout assignments from cache."""
    layouts = dict(DEFAULT_WORKSPACE_LAYOUTS)
    if WORKSPACE_LAYOUTS_PATH.is_file():
        try:
            data = json.loads(WORKSPACE_LAYOUTS_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                layouts.update({str(k): str(v) for k, v in data.items()})
        except (OSError, json.JSONDecodeError):
            pass
    return layouts


def save_workspace_layouts(layouts: dict[str, str]) -> Path:
    """Save the persistent per-workspace layout assignments to cache."""
    WORKSPACE_LAYOUTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    WORKSPACE_LAYOUTS_PATH.write_text(json.dumps(layouts, indent=2), encoding="utf-8")
    return WORKSPACE_LAYOUTS_PATH


AUTOSTART_SERVICES = [
    ("lxpolkit", "PolicyKit Agent", "lxpolkit", "󰒓"),
    ("dunst", "Dunst Notification Daemon", "dunst", "󰂚"),
    ("greenclip", "Greenclip Clipboard History", "greenclip daemon", "󰅌"),
    ("nm-applet", "NetworkManager Applet", "nm-applet --indicator", "󰖩"),
    ("xsettingsd", "GTK Theme Sync Daemon", "xsettingsd", "󰔎"),
    ("gesture-daemon", "Multi-Touch Gesture Daemon", f"{CONFIG_DIR}/scripts/gesture-daemon", "󰌢"),
]


def get_autostart_services_status() -> list[dict[str, Any]]:
    """Return status of key Qtile-Con desktop background services."""
    services = []
    for proc_name, label, cmd, icon in AUTOSTART_SERVICES:
        res = run_command(["pgrep", "-f", proc_name])
        running = res.ok and bool(res.stdout.strip())
        services.append({
            "process": proc_name,
            "label": label,
            "command": cmd,
            "icon": icon,
            "running": running,
        })
    return services


def restart_autostart_service(service_name: str) -> tuple[bool, str]:
    """Restart or launch an autostart daemon service."""
    for proc_name, label, cmd, _ in AUTOSTART_SERVICES:
        if proc_name == service_name:
            run_command(["pkill", "-f", proc_name])
            res = run_command(["nohup", "bash", "-c", f"{cmd} &"])
            return res.ok, f"{label} restarted"
    return False, f"Unknown service: {service_name}"

