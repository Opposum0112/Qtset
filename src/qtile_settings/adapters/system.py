"""System statistics and diagnostic adapter.

Gathers hardware utilization metrics (CPU, RAM, storage via `psutil`), formats
display output geometry via `xrandr`, converts ANSI TrueColor escape sequences
to rich text HTML, and extracts the authentic Qtile block-art logo from Fastfetch.
"""

from __future__ import annotations

import json
import os
import platform
import re
import shutil
from pathlib import Path

import psutil

from qtile_settings.adapters.commands import run_command

FASTFETCH_CONFIG_PATH = Path.home() / ".config" / "fastfetch" / "config.jsonc"

FALLBACK_QTILE_LOGO_SOURCE = (
    "  \x1b[38;2;203;166;247m▄██████▄\x1b[0m  \n"
    " \x1b[38;2;203;166;247m██▀    ▀██\x1b[0m \n"
    " \x1b[38;2;180;190;254m██      ██\x1b[0m \n"
    " \x1b[38;2;137;180;250m██      ██\x1b[0m \n"
    " \x1b[38;2;137;220;235m██▄    ▄██\x1b[0m \n"
    "  \x1b[38;2;148;226;213m▀██████▀\x1b[0m  \n"
    "        \x1b[38;2;243;139;168m▀██\x1b[0m \n"
    "    \x1b[1;38;2;203;166;247mQTILE\x1b[0m   "
)


def ansi_to_html(ansi_str: str) -> str:
    """Convert ANSI escape sequences (24-bit TrueColor and bold) to rich text HTML."""
    ansi_pattern = re.compile(r"\x1b\[([0-9;]*)m")
    html_parts: list[str] = []
    last_end = 0
    open_spans = 0

    for match in ansi_pattern.finditer(ansi_str):
        text = ansi_str[last_end : match.start()]
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        html_parts.append(text)

        codes = match.group(1).split(";") if match.group(1) else ["0"]

        if codes in (["0"], [""]):
            while open_spans > 0:
                html_parts.append("</span>")
                open_spans -= 1
        elif len(codes) == 5 and codes[0] == "38" and codes[1] == "2":
            r, g, b = codes[2], codes[3], codes[4]
            html_parts.append(f'<span style="color: rgb({r}, {g}, {b});">')
            open_spans += 1
        elif len(codes) == 6 and codes[0] == "1" and codes[1] == "38" and codes[2] == "2":
            r, g, b = codes[3], codes[4], codes[5]
            html_parts.append(f'<span style="color: rgb({r}, {g}, {b}); font-weight: bold;">')
            open_spans += 1
        elif codes == ["1"]:
            html_parts.append('<span style="font-weight: bold;">')
            open_spans += 1

        last_end = match.end()

    text = ansi_str[last_end:]
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    html_parts.append(text)

    while open_spans > 0:
        html_parts.append("</span>")
        open_spans -= 1

    content = "".join(html_parts)
    return (
        f'<pre style="margin: 0; padding: 0; '
        f"font-family: 'JetBrainsMono Nerd Font', 'JetBrains Mono', monospace; "
        f'font-size: 11px; line-height: 100%; font-weight: bold;">{content}</pre>'
    )


def get_fastfetch_qtile_logo_html(config_path: Path | None = None) -> str:
    """Read the Qtile ASCII / Unicode logo from fastfetch config and return HTML for QLabel."""
    path = config_path or FASTFETCH_CONFIG_PATH
    raw_source: str | None = None

    if path.is_file():
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            match = re.search(r'"source"\s*:\s*"((?:[^"\\]|\\.)*)"', content)
            if match:
                raw_source = json.loads(f'"{match.group(1)}"')
            else:
                data = json.loads(content, strict=False)
                raw_source = data.get("logo", {}).get("source")
        except (json.JSONDecodeError, OSError, TypeError, KeyError):
            raw_source = None

    if not raw_source:
        raw_source = FALLBACK_QTILE_LOGO_SOURCE

    return ansi_to_html(raw_source)


def get_os_display_name() -> str:
    """Return a clean user-facing OS name (e.g. 'Parrot Security 7.3' or 'Arch Linux')."""
    try:
        data = platform.freedesktop_os_release()
        return data.get("PRETTY_NAME") or data.get("NAME") or platform.system()
    except (AttributeError, OSError):
        return platform.system()


def system_summary() -> dict[str, str | int | float]:
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage(os.path.expanduser("~"))
    return {
        "hostname": platform.node() or "Unknown",
        "os": get_os_display_name(),
        "python": platform.python_version(),
        "cpu_percent": psutil.cpu_percent(interval=None),
        "memory_percent": memory.percent,
        "memory_used_gib": round(memory.used / (1024 ** 3), 1),
        "memory_total_gib": round(memory.total / (1024 ** 3), 1),
        "disk_percent": disk.percent,
        "disk_free_gib": round(disk.free / (1024 ** 3), 1),
    }


def display_summary() -> str:
    if os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland":
        return "This project targets X11; the current session reports Wayland."
    result = run_command(["xrandr", "--current"])
    if not result.ok:
        return result.error
    lines = [line.strip() for line in result.stdout.splitlines()
             if " connected" in line or "*" in line]
    return "\n".join(lines[:8]) or "No display information reported."


def available_tools() -> dict[str, bool]:
    return {name: shutil.which(name) is not None for name in ("xrandr", "nmcli", "wpctl", "bluetoothctl")}
