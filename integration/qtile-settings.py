# ==============================================================================
# Qtile Standalone / Monolithic config.py Keybindings Integration Snippet
# Merge these definitions into `~/.config/qtile/config.py` when not using modular keys.py.
# ==============================================================================
from libqtile.config import Key
from libqtile.lazy import lazy

# Add to your existing keys list:
settings_keys = [
    Key(["mod4"], "s", lazy.spawn("qtile-settings"), desc="Open Qtile Settings & Command Center"),
    Key(["mod4", "shift"], "s", lazy.spawn("qtile-settings --quick"), desc="Open Qtile Quick Settings"),
]

# Append to your configuration keys list:
# keys.extend(settings_keys)
