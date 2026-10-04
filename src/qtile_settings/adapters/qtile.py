"""Qtile window manager IPC and process adapter.

Communicates with the running Qtile window manager instance over IPC (`qtile cmd-obj`),
runs syntax validation checks (`qtile check`), tails runtime logs, and queries active layout
assignments.
"""

from __future__ import annotations

import os
from pathlib import Path

from qtile_settings.adapters.commands import run_command

CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "qtile"
CONFIG_FILE = CONFIG_DIR / "config.py"
LOG_FILE = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "qtile" / "qtile.log"


def config_path() -> Path:
    return CONFIG_FILE


def reload_qtile() -> tuple[bool, str]:
    """Reload Qtile configuration dynamically via IPC without restarting processes."""
    result = run_command(["qtile", "cmd-obj", "-o", "cmd", "-f", "reload_config"])
    return result.ok, result.error or "Qtile configuration reloaded."


def restart_qtile() -> tuple[bool, str]:
    """Restart Qtile window manager state via IPC."""
    result = run_command(["qtile", "cmd-obj", "-o", "cmd", "-f", "restart"])
    return result.ok, result.error or "Qtile restart initiated."


def check_config() -> tuple[bool, str]:
    """Run Qtile's built-in syntax and structure validation."""
    if not CONFIG_FILE.is_file():
        return False, f"Config file not found at {CONFIG_FILE}"
    result = run_command(["qtile", "check", "-c", str(CONFIG_FILE)], timeout=15.0)
    return result.ok, result.stdout or result.error or "Qtile configuration check passed."


def get_qtile_version() -> str:
    """Return the installed Qtile version."""
    result = run_command(["qtile", "--version"], timeout=3.0)
    return result.stdout if result.ok else "Unknown"


def get_qtile_log(max_lines: int = 50) -> str:
    """Read the latest lines from Qtile's runtime log."""
    if not LOG_FILE.is_file():
        return f"Log file not found at {LOG_FILE}"
    try:
        lines = LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
        tail = lines[-max_lines:] if len(lines) > max_lines else lines
        return "\n".join(tail) or "Log file is empty."
    except OSError as exc:
        return f"Could not read Qtile log: {exc}"


def get_current_layout() -> str:
    """Return the current Qtile layout name from cache or fallback."""
    cache_file = Path.home() / ".cache" / "qtile-current-layout"
    if cache_file.is_file():
        try:
            val = cache_file.read_text(encoding="utf-8").strip()
            if val:
                return val
        except OSError:
            pass
    return "Niri Scroller Ribbon"
