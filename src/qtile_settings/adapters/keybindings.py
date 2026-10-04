"""Keybindings adapter and shortcut catalog.

Parses Qtile Key objects statically from keys.py using Python's AST parser, generates
human-readable descriptions and category tags matching the Qtile-Con cheatsheet, and
safely serializes user edits back to disk with automatic timestamped backups.
"""

from __future__ import annotations

import ast
import re
import uuid
from dataclasses import dataclass
from pathlib import Path

from qtile_settings.adapters.configuration import CONFIG_DIR, _backup

KEYS_PATH = CONFIG_DIR / "qtile_config" / "keys.py"

MOD_DISPLAY = {
    "MOD": "Super",
    "mod4": "Super",
    "mod1": "Alt",
    "control": "Ctrl",
    "shift": "Shift",
}

# Authoritative command lookup matching Qtile-Con keybindings cheatsheet
CMD_DESCRIPTIONS: dict[str, tuple[str, str, str]] = {
    "screenshot full": ("󰄄", "Screenshots", "Fullscreen Screenshot (Mac Ergonomics: Cmd+Shift+3)"),
    "screenshot region": ("󰄄", "Screenshots", "Area / Window Screenshot to File (Cmd+Shift+4)"),
    "screenshot clipboard": ("󰄄", "Screenshots", "Area Screenshot Directly to Clipboard (Cmd+Shift+Ctrl+4)"),
    "pamixer --increase": ("󰕾", "Hardware & Media", "Increase Master Volume (+5%)"),
    "pamixer --decrease": ("󰕾", "Hardware & Media", "Decrease Master Volume (-5%)"),
    "pamixer --toggle-mute": ("󰕾", "Hardware & Media", "Toggle Audio Output Mute / Unmute"),
    "brightnessctl set +5%": ("󰃠", "Hardware & Media", "Increase Screen Brightness (+5%)"),
    "brightnessctl set 5%-": ("󰃞", "Hardware & Media", "Decrease Screen Brightness (-5%)"),
    "brightnessctl --device='*kbd*' set +10%": ("󰌌", "Hardware & Media", "Increase Keyboard Backlight (+10%)"),
    "brightnessctl --device='*kbd*' set 10%-": ("󰌌", "Hardware & Media", "Decrease Keyboard Backlight (-10%)"),
    "qtile-action launcher": ("󰍉", "Applications & Launchers", "Application Launcher (Rofi Combi: Apps & Run)"),
    "qtile-action run": ("󰌌", "Applications & Launchers", "Run Command / CLI Binary Launcher (Rofi run)"),
    "qtile-action cheatsheet": ("󰌌", "Applications & Launchers", "Keybinding Cheatsheet & Reference Palette (8-Tab)"),
    "qtile-action configs": ("󰒓", "Applications & Launchers", "Environment Configuration Files Browser"),
    "qtile-action clipboard": ("󰅍", "Applications & Launchers", "Clipboard History Manager (Greenclip / Rofi)"),
    "qtile-action slider": ("󰕾", "Hardware & Media", "Interactive Floating Volume Slider & Sinks"),
    "qtile-action man": ("󰈙", "Applications & Launchers", "Manual Pages & Documentation Lookup (Rofi man)"),
    "qtile-action restore all": ("󰖯", "Window Management", "Restore All Minimized Windows on Current Workspace"),
    "qtile-action restore": ("󰖯", "Window Management", "Browse & Restore Minimized Windows (Rofi)"),
    "qtile-action layout": ("󰕰", "Layout & Navigation", "Layout Selector Menu (Columns, Scroller, Monad)"),
    "set-theme": ("󰏘", "Applications & Launchers", "Global Theme Selector (Catppuccin, Gruvbox, etc.)"),
    "set-wallpaper": ("󰸉", "Applications & Launchers", "Wallpaper & Font Thumbnail Grid Selector"),
    "logout-menu": ("󰐥", "Window Management", "Power & Session Logout Menu (Lock, Reboot, Poweroff)"),
    "i3lock": ("󰌾", "Window Management", "Instant Screen Lock (i3lock)"),
    "TERMINAL -e yazi": ("󰒋", "Applications & Launchers", "Launch Yazi Terminal File Manager"),
    "yazi": ("󰒋", "Applications & Launchers", "Launch Yazi Terminal File Manager"),
    "thunar": ("󰉋", "Applications & Launchers", "Launch Thunar Graphical File Manager"),
    "TERMINAL": ("󰆍", "Applications & Launchers", "Spawn Terminal Emulator"),
    "LAUNCHER": ("󰍉", "Applications & Launchers", "Application Launcher (Rofi Combi: Apps & Run)"),
}

# Authoritative lazy command lookup matching Qtile-Con keybindings cheatsheet
LAZY_DESCRIPTIONS: dict[str, tuple[str, str, str]] = {
    "restart": ("󰑐", "Window Management", "Restart / Reload Qtile In-Place"),
    "kill": ("󰅚", "Window Management", "Close / Kill Focused Window"),
    "next_layout": ("󰕰", "Layout & Navigation", "Cycle to Next Tiling Layout"),
    "prev_layout": ("󰕰", "Layout & Navigation", "Cycle to Previous Tiling Layout"),
    "toggle_maximize": ("󰊓", "Window Management", "Toggle Active Window Maximize (With Borders)"),
    "toggle_minimize": ("󰊒", "Window Management", "Minimize Active Window (Hide & Exclude)"),
    "toggle_floating": ("󰉈", "Window Management", "Toggle Floating Window Mode"),
    "toggle_fullscreen": ("󰊓", "Window Management", "Toggle Fullscreen Window Mode"),
    "cycle_width": ("󰤼", "Layout & Navigation", "Cycle Scroller Column Width (1/3, 1/2, 2/3, Full)"),
    "grow_width": ("󰤼", "Layout & Navigation", "Expand Scroller Column Width in Viewport"),
    "shrink_width": ("󰤼", "Layout & Navigation", "Shrink Scroller Column Width in Viewport"),
    "center": ("󰤼", "Layout & Navigation", "Center Active Scroller Column in Viewport"),
    "toggle_split": ("󰤼", "Layout & Navigation", "Toggle Scroller Column Split / Stacked Mode"),
    "expel": ("󰤼", "Layout & Navigation", "Expel Focused Window to New Scroller Column"),
    "consume_left": ("󰤼", "Layout & Navigation", "Consume / Merge Adjacent Column to Left"),
    "consume_right": ("󰤼", "Layout & Navigation", "Consume / Merge Adjacent Column to Right"),
    "left": ("󰁍", "Layout & Navigation", "Focus Window to the Left"),
    "right": ("󰁔", "Layout & Navigation", "Focus Window to the Right"),
    "up": ("󰁝", "Layout & Navigation", "Focus Window Upwards"),
    "down": ("󰁅", "Layout & Navigation", "Focus Window Downwards"),
    "shuffle_left": ("󰁍", "Layout & Navigation", "Shuffle Focused Window to the Left"),
    "shuffle_right": ("󰁔", "Layout & Navigation", "Shuffle Focused Window to the Right"),
    "shuffle_up": ("󰁝", "Layout & Navigation", "Shuffle Focused Window Upwards"),
    "shuffle_down": ("󰁅", "Layout & Navigation", "Shuffle Focused Window Downwards"),
    "next_group": ("󰮯", "Workspaces", "Switch to Next Workspace"),
    "prev_group": ("󰮯", "Workspaces", "Switch to Previous Workspace"),
    "restore_minimized_window": ("󰖯", "Window Management", "Restore Most Recently Minimized Window"),
    "restore_all_minimized_windows": ("󰖯", "Window Management", "Restore All Minimized Windows on Workspace"),
    "window_to_prev_group": ("󰮯", "Workspaces", "Move Focused Window to Previous Workspace & Follow"),
    "window_to_next_group": ("󰮯", "Workspaces", "Move Focused Window to Next Workspace & Follow"),
}


@dataclass
class KeybindingItem:
    id: str
    modifiers: list[str]
    key: str
    action: str
    description: str
    category: str
    icon: str = "󰌌"
    raw_code: str = ""

    @property
    def display_combo(self) -> str:
        mods = [MOD_DISPLAY.get(m, m.capitalize()) for m in self.modifiers]
        key_str = self.key
        if key_str == "Return":
            key_str = "Enter"
        elif key_str == "space":
            key_str = "Space"
        elif key_str == "slash":
            key_str = "/"
        elif key_str == "question":
            key_str = "?"
        elif key_str == "bracketleft":
            key_str = "["
        elif key_str == "bracketright":
            key_str = "]"
        elif key_str == "equal":
            key_str = "="
        elif key_str == "minus":
            key_str = "-"
        elif key_str == "period":
            key_str = ". (Period)"
        elif key_str == "comma":
            key_str = ", (Comma)"
        elif key_str.startswith("XF86"):
            key_str = key_str.replace("XF86", "")
        return " + ".join(mods + [key_str])


def _categorize_and_describe(action_str: str, explicit_desc: str = "") -> tuple[str, str, str]:
    """Resolve icon, category, and human-readable description for an action string."""
    if explicit_desc:
        desc = explicit_desc
    else:
        desc = ""

    # Check command-based actions (lazy.spawn)
    if "lazy.spawn(" in action_str:
        for needle in sorted(CMD_DESCRIPTIONS.keys(), key=len, reverse=True):
            if needle in action_str:
                icon, cat, needle_desc = CMD_DESCRIPTIONS[needle]
                return icon, cat, explicit_desc or needle_desc
        # Fallback for other spawn actions
        cmd_part = action_str.replace("lazy.spawn(", "").rstrip(")")
        clean_cmd = cmd_part.strip("'\"")
        return "󰆍", "Applications & Launchers", explicit_desc or f"Launch: {clean_cmd}"

    # Check lazy functions with word boundary protection
    for lazy_key in sorted(LAZY_DESCRIPTIONS.keys(), key=len, reverse=True):
        icon, cat, lazy_desc = LAZY_DESCRIPTIONS[lazy_key]
        if (
            f".{lazy_key}(" in action_str
            or f"lazy.{lazy_key}()" in action_str
            or action_str == lazy_key
            or action_str.endswith(f".{lazy_key}")
            or re.search(rf"\b{re.escape(lazy_key)}\b", action_str)
        ):
            return icon, cat, explicit_desc or lazy_desc

    # Workspace tag switching / moving
    if "toscreen()" in action_str:
        return "󰮯", "Workspaces", explicit_desc or "Switch to Workspace Tag"
    if "togroup(" in action_str:
        return "󰮯", "Workspaces", explicit_desc or "Move Focused Window to Workspace Tag & Follow"

    return "󰌌", "Custom & Other", desc or action_str


def read_keybindings(path: Path | None = None) -> list[KeybindingItem]:
    """Parse Key(...) declarations from qtile_config/keys.py safely without code execution."""
    keys_file = path or KEYS_PATH
    if not keys_file.is_file():
        return []

    source = keys_file.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(keys_file))
    except (SyntaxError, OSError):
        return []

    items: list[KeybindingItem] = []

    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "keys" and isinstance(node.value, ast.List):
                    for elt in node.value.elts:
                        if isinstance(elt, ast.Call):
                            func_name = getattr(elt.func, "id", "")
                            if func_name == "Key" and len(elt.args) >= 3:
                                # Modifiers
                                mods: list[str] = []
                                if isinstance(elt.args[0], ast.List):
                                    for m in elt.args[0].elts:
                                        if isinstance(m, ast.Name):
                                            mods.append(m.id)
                                        elif isinstance(m, ast.Constant):
                                            mods.append(str(m.value))
                                # Key
                                key_str = ""
                                if isinstance(elt.args[1], ast.Constant):
                                    key_str = str(elt.args[1].value)
                                elif isinstance(elt.args[1], ast.Name):
                                    key_str = elt.args[1].id

                                # Action
                                action_str = ast.unparse(elt.args[2])

                                # Optional explicit desc keyword argument
                                desc_str = ""
                                for kw in elt.keywords:
                                    if kw.arg == "desc" and isinstance(kw.value, ast.Constant):
                                        desc_str = str(kw.value.value)

                                icon, cat, desc = _categorize_and_describe(action_str, desc_str)
                                raw = ast.unparse(elt)

                                items.append(KeybindingItem(
                                    id=str(uuid.uuid4())[:8],
                                    modifiers=mods,
                                    key=key_str,
                                    action=action_str,
                                    description=desc,
                                    category=cat,
                                    icon=icon,
                                    raw_code=raw,
                                ))

    return items


def serialize_keybinding(item: KeybindingItem) -> str:
    """Format a KeybindingItem as a clean Python Key(...) line."""
    mod_reprs = []
    for m in item.modifiers:
        if m in ("MOD", "mod4") and not m.startswith("'"):
            mod_reprs.append("MOD")
        else:
            mod_reprs.append(repr(m))
    mods_code = f"[{', '.join(mod_reprs)}]"
    desc_arg = f', desc={item.description!r}' if item.description else ""
    return f"Key({mods_code}, {item.key!r}, {item.action}{desc_arg})"


def save_keybindings(items: list[KeybindingItem], path: Path | None = None) -> Path:
    """Save the updated list of keybindings to keys.py, creating a backup and validating syntax."""
    keys_file = path or KEYS_PATH
    if not keys_file.is_file():
        raise FileNotFoundError(f"Keys file not found: {keys_file}")

    original = keys_file.read_text(encoding="utf-8")

    key_lines = []
    current_category = ""
    for item in items:
        if item.category != current_category:
            current_category = item.category
            key_lines.append(f"\n    # --- {current_category} ---")
        line = f"    {serialize_keybinding(item)},"
        key_lines.append(line)

    keys_block = "keys = [" + "\n".join(key_lines) + "\n]"

    pattern = r"(?s)keys\s*=\s*\[.*?\](?=\n\n|\n# ---|\nfor|\Z)"
    if re.search(pattern, original):
        updated = re.sub(pattern, keys_block, original, count=1)
    else:
        pattern_fallback = r"(?s)keys\s*=\s*\[.*\]"
        updated = re.sub(pattern_fallback, keys_block, original, count=1)

    ast.parse(updated, filename=str(keys_file))
    _backup(keys_file)
    keys_file.write_text(updated, encoding="utf-8")
    return keys_file
