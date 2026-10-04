# ruff: noqa: F821
# ==============================================================================
# Qtile-Con Modular Keybindings Integration Snippet
# Append these entries into the existing `keys` list in `~/.config/qtile/qtile_config/keys.py`.
# `MOD` and `lazy` are already imported by Qtile-Con's modular keys.py.
# ==============================================================================
from libqtile.config import Key
from libqtile.lazy import lazy

# Super + S: Full Settings Center | Super + Shift + S: Quick Settings Popup
keys.extend([
    Key([MOD], "s", lazy.spawn("qtile-settings"), desc="Open Qtile Settings & Command Center"),
    Key([MOD, "shift"], "s", lazy.spawn("qtile-settings --quick"), desc="Open Qtile Quick Settings"),
])
