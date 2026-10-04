from __future__ import annotations

from pathlib import Path

import pytest

from qtile_settings.adapters import configuration
from qtile_settings.adapters.commands import CommandResult


def setup_config(tmp_path: Path, monkeypatch):
    config_dir = tmp_path / ".config" / "qtile"
    package = config_dir / "qtile_config"
    package.mkdir(parents=True)
    settings = package / "settings.py"
    settings.write_text(
        'import os\nMOD = "mod4"\nTERMINAL = os.environ.get("QTILE_TERMINAL", "xterm")\n'
        'GAP = 8\nBORDER_WIDTH = 2\nBAR_HEIGHT = 36\nFONT = "JetBrainsMono Nerd Font"\nFONT_SIZE = 12\n'
        'LAUNCHER = "rofi -show drun"\nWALLPAPER_DIR = "~/Pictures/Wallpapers"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(configuration, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(configuration, "SETTINGS_PATH", settings)
    return config_dir, settings


def test_save_settings_makes_backup_and_preserves_unmanaged_lines(tmp_path, monkeypatch):
    _, settings = setup_config(tmp_path, monkeypatch)
    values = configuration.read_settings()
    values["GAP"] = 12
    values["TERMINAL"] = "alacritty"
    configuration.save_settings(values)
    content = settings.read_text(encoding="utf-8")
    assert "GAP = 12" in content
    assert "TERMINAL = 'alacritty'" in content
    assert "import os" in content
    assert list(settings.parent.glob("settings.py.backup.*"))


def test_save_file_rejects_invalid_python_and_does_not_overwrite(tmp_path, monkeypatch):
    config_dir, _ = setup_config(tmp_path, monkeypatch)
    target = config_dir / "config.py"
    target.write_text("valid = True\n", encoding="utf-8")
    with pytest.raises(SyntaxError):
        configuration.save_file("config.py", "if True print('invalid')")
    assert target.read_text(encoding="utf-8") == "valid = True\n"


def test_save_file_rejects_path_traversal(tmp_path, monkeypatch):
    setup_config(tmp_path, monkeypatch)
    with pytest.raises(ValueError):
        configuration.save_file("../outside.py", "valid = True")


def test_read_config_settings_defaults(tmp_path, monkeypatch):
    setup_config(tmp_path, monkeypatch)
    # config.py does not exist yet
    prefs = configuration.read_config_settings()
    assert prefs["auto_fullscreen"] is True
    assert prefs["focus_on_window_activation"] == "smart"
    assert prefs["follow_mouse_focus"] is True


def test_read_config_settings_custom(tmp_path, monkeypatch):
    config_dir, _ = setup_config(tmp_path, monkeypatch)
    config_py = config_dir / "config.py"
    config_py.write_text(
        'auto_fullscreen = False\nfollow_mouse_focus = False\nwmname = "qtile"\n',
        encoding="utf-8",
    )
    prefs = configuration.read_config_settings()
    assert prefs["auto_fullscreen"] is False
    assert prefs["follow_mouse_focus"] is False
    assert prefs["wmname"] == "qtile"
    # Defaults should remain for unmentioned keys
    assert prefs["focus_on_window_activation"] == "smart"


def test_read_all_preferences(tmp_path, monkeypatch):
    config_dir, _ = setup_config(tmp_path, monkeypatch)
    config_py = config_dir / "config.py"
    config_py.write_text('follow_mouse_focus = False\n', encoding="utf-8")
    all_prefs = configuration.read_all_preferences()
    assert all_prefs["GAP"] == 8
    assert all_prefs["MOD"] == "mod4"
    assert all_prefs["follow_mouse_focus"] is False


def test_save_config_settings(tmp_path, monkeypatch):
    config_dir, _ = setup_config(tmp_path, monkeypatch)
    config_py = config_dir / "config.py"
    config_py.write_text(
        '# Window manager\nauto_fullscreen = True\nfollow_mouse_focus = True\nwmname = "LG3D"\n',
        encoding="utf-8",
    )
    configuration.save_config_settings({"follow_mouse_focus": False, "cursor_warp": True})
    content = config_py.read_text(encoding="utf-8")
    assert "follow_mouse_focus = False" in content
    assert "cursor_warp = True" in content
    assert "# Window manager" in content
    assert list(config_dir.glob("config.py.backup.*"))


def test_save_preference(tmp_path, monkeypatch):
    config_dir, settings = setup_config(tmp_path, monkeypatch)
    config_py = config_dir / "config.py"
    config_py.write_text('follow_mouse_focus = True\n', encoding="utf-8")

    # Preference in settings.py
    configuration.save_preference("GAP", 14)
    assert "GAP = 14" in settings.read_text(encoding="utf-8")

    # Preference in config.py
    configuration.save_preference("follow_mouse_focus", False)
    assert "follow_mouse_focus = False" in config_py.read_text(encoding="utf-8")

    # Unknown preference key
    with pytest.raises(KeyError):
        configuration.save_preference("nonexistent_preference_key", 123)


def test_workspace_layouts_cache(tmp_path, monkeypatch):
    cache_file = tmp_path / "workspace_layouts.json"
    monkeypatch.setattr(configuration, "WORKSPACE_LAYOUTS_PATH", cache_file)

    # Defaults when file doesn't exist
    layouts = configuration.read_workspace_layouts()
    assert layouts["1"] == "columns"
    assert layouts["2"] == "scroller"

    # Save custom layouts
    layouts["1"] = "max"
    layouts["2"] = "monadtall"
    configuration.save_workspace_layouts(layouts)

    # Read back
    reloaded = configuration.read_workspace_layouts()
    assert reloaded["1"] == "max"
    assert reloaded["2"] == "monadtall"


def test_autostart_services_status(monkeypatch):
    monkeypatch.setattr(
        configuration,
        "run_command",
        lambda cmd, timeout=15: CommandResult(ok=True, stdout="1234\n", error="")
    )
    svcs = configuration.get_autostart_services_status()
    assert len(svcs) == 6
    assert any(s["process"] == "dunst" and s["running"] is True for s in svcs)


def test_restore_defaults(tmp_path, monkeypatch):
    config_dir, settings = setup_config(tmp_path, monkeypatch)
    config_py = config_dir / "config.py"
    config_py.write_text('follow_mouse_focus = False\n', encoding="utf-8")
    monkeypatch.setattr(configuration, "CONFIG_PATH", config_py)

    # Change settings
    configuration.save_preference("GAP", 30)
    assert "GAP = 30" in settings.read_text(encoding="utf-8")

    # Restore defaults
    ok, msg = configuration.restore_defaults()
    assert ok is True
    assert "restored" in msg.lower()

    # Verify settings reset
    prefs = configuration.read_all_preferences()
    assert prefs["GAP"] == configuration.SETTINGS_DEFAULTS["GAP"]
    assert prefs["follow_mouse_focus"] == configuration.CONFIG_DEFAULTS["follow_mouse_focus"]


def test_backups_list_and_restore(tmp_path, monkeypatch):
    _config_dir, settings = setup_config(tmp_path, monkeypatch)

    # Save to create a backup
    configuration.save_settings({"GAP": 16})
    backups = configuration.list_backups()
    assert len(backups) >= 1
    assert backups[0]["target_name"] == "settings.py"
    assert backups[0]["path"].is_file()

    # Now change value
    configuration.save_settings({"GAP": 24})
    assert "GAP = 24" in settings.read_text(encoding="utf-8")

    # Restore the backup (which had GAP = 8 or initial)
    first_backup = backups[0]["path"]
    ok, msg = configuration.restore_backup(first_backup)
    assert ok is True
    assert "Restored" in msg
    assert "GAP = 8" in settings.read_text(encoding="utf-8") or "GAP = 16" in settings.read_text(encoding="utf-8")


