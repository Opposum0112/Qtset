from __future__ import annotations

import pytest

from qtile_settings.adapters import keybindings

SAMPLE_KEYS_CONTENT = """
from libqtile.config import Key
from libqtile.lazy import lazy
from qtile_config.settings import MOD, TERMINAL, SCRIPTS

keys = [
    Key([MOD], "Return", lazy.spawn(TERMINAL)),
    Key([MOD, "shift"], "q", lazy.window.kill()),
    Key([MOD, "control"], "r", lazy.restart()),
    Key([MOD], "d", lazy.spawn(f"{SCRIPTS}/qtile-action launcher")),
    Key([MOD], "f", lazy.window.toggle_fullscreen()),
]
"""


def test_read_keybindings_parsed(tmp_path):
    keys_file = tmp_path / "keys.py"
    keys_file.write_text(SAMPLE_KEYS_CONTENT, encoding="utf-8")

    items = keybindings.read_keybindings(keys_file)
    assert len(items) == 5

    return_item = next(it for it in items if it.key == "Return")
    assert return_item.display_combo == "Super + Enter"
    assert "TERMINAL" in return_item.action
    assert return_item.category == "Applications & Launchers"

    kill_item = next(it for it in items if it.key == "q")
    assert kill_item.display_combo == "Super + Shift + q"
    assert kill_item.action == "lazy.window.kill()"
    assert kill_item.category == "Window Management"


def test_serialize_and_save_keybindings(tmp_path):
    keys_file = tmp_path / "keys.py"
    keys_file.write_text(SAMPLE_KEYS_CONTENT, encoding="utf-8")

    items = keybindings.read_keybindings(keys_file)

    # Modify an existing keybinding
    items[0].key = "space"
    items[0].description = "Custom Spawn Action"

    # Add a new keybinding
    new_item = keybindings.KeybindingItem(
        id="custom1",
        modifiers=["MOD", "control"],
        key="t",
        action="lazy.spawn('alacritty')",
        description="Launch Alacritty",
        category="Applications & Launchers",
    )
    items.append(new_item)

    saved_path = keybindings.save_keybindings(items, path=keys_file)
    assert saved_path == keys_file

    # Verify content written and syntax valid
    updated_items = keybindings.read_keybindings(keys_file)
    assert len(updated_items) == 6
    assert any(it.key == "space" for it in updated_items)
    assert any(it.key == "t" and "control" in it.modifiers for it in updated_items)

    # Verify backup created
    assert list(tmp_path.glob("keys.py.backup.*"))


def test_read_keybindings_nonexistent():
    items = keybindings.read_keybindings(keybindings.Path("/nonexistent/keys.py"))
    assert items == []


def test_save_keybindings_nonexistent():
    with pytest.raises(FileNotFoundError):
        keybindings.save_keybindings([], path=keybindings.Path("/nonexistent/keys.py"))


def test_keybindings_categorize_and_describe_accurate():
    # Test that window_to_prev_group does not falsely match 'up'
    icon, cat, desc = keybindings._categorize_and_describe("window_to_prev_group")
    assert cat == "Workspaces"
    assert "Previous Workspace" in desc
    assert "Upwards" not in desc

    # Test LAUNCHER command
    icon, cat, desc = keybindings._categorize_and_describe("lazy.spawn(LAUNCHER)")
    assert cat == "Applications & Launchers"
    assert "Launcher" in desc

    # Test volume pamixer
    icon, cat, desc = keybindings._categorize_and_describe("lazy.spawn('pamixer --increase 5')")
    assert icon == "󰕾"
    assert cat == "Hardware & Media"
    assert "Volume" in desc
