from __future__ import annotations

import stat
import subprocess
from pathlib import Path

from qtile_settings.adapters import (
    configuration,
    input_devices,
    keybindings,
    qtile,
    themes,
)


def test_qtile_con_config_path_exists():
    """Verify that the active Qtile configuration path is resolved properly."""
    cfg = qtile.config_path()
    assert isinstance(cfg, Path)
    assert cfg.name == "config.py"


def test_qtile_con_keys_parsing():
    """Verify that Qtile-Con's modular keys.py can be parsed and categorized without errors."""
    keys_file = Path.home() / ".config" / "qtile" / "qtile_config" / "keys.py"
    if keys_file.is_file():
        items = keybindings.read_keybindings()
        assert len(items) >= 50
        categories = {item.category for item in items}
        assert "Applications & Launchers" in categories
        assert any(item.key == "Return" for item in items)


def test_qtile_con_preferences_reading():
    """Verify that all preferences can be read from the live Qtile-Con environment."""
    prefs = configuration.read_all_preferences()
    assert isinstance(prefs, dict)
    assert "GAP" in prefs
    assert "BORDER_WIDTH" in prefs
    assert "BAR_HEIGHT" in prefs
    assert "MOD" in prefs


def test_qtile_con_themes_available():
    """Verify that themes are discovered from the Qtile-Con themes directory."""
    available = themes.list_themes()
    assert len(available) >= 1
    palette = themes.get_theme_palette(available[0])
    assert "surface" in palette or "base" in palette


def test_qtile_con_kbd_backlight_adapter():
    """Verify keyboard backlight detection and read functionality."""
    dev = input_devices.find_kbd_backlight_device()
    has_kbd = input_devices.has_kbd_backlight()
    if dev:
        assert has_kbd is True
        val, _ = input_devices.get_kbd_backlight()
        if val is not None:
            assert 0 <= val <= 100
    else:
        assert has_kbd is False


def test_install_and_uninstall_scripts_executable():
    """Verify install and uninstall scripts exist, are executable, and contain no hardcoded PII."""
    repo_root = Path(__file__).resolve().parent.parent
    install_sh = repo_root / "integration" / "install.sh"
    uninstall_sh = repo_root / "integration" / "uninstall.sh"

    assert install_sh.is_file()
    assert uninstall_sh.is_file()

    # Check executable permission
    assert bool(install_sh.stat().st_mode & stat.S_IXUSR)
    assert bool(uninstall_sh.stat().st_mode & stat.S_IXUSR)

    # Verify no hardcoded current username in the scripts
    import getpass
    curr_user = getpass.getuser()
    for script in [install_sh, uninstall_sh]:
        text = script.read_text(encoding="utf-8")
        if curr_user and curr_user != "root":
            assert curr_user not in text
        assert "set -euo pipefail" in text


def test_qtile_check_validation():
    """Verify that Qtile's built-in syntax and type-checker validates the config cleanly."""
    cfg = Path.home() / ".config" / "qtile" / "config.py"
    if cfg.is_file():
        res = subprocess.run(["qtile", "check", "-c", str(cfg)], capture_output=True, text=True, check=False)
        assert res.returncode == 0
        assert "Success" in res.stdout


def test_nix_flake_and_default_configuration_files():
    """Verify flake.nix and default.nix exist and contain required derivation definitions."""
    repo_root = Path(__file__).resolve().parent.parent
    flake = repo_root / "flake.nix"
    default_nix = repo_root / "default.nix"

    assert flake.is_file()
    assert default_nix.is_file()

    flake_text = flake.read_text(encoding="utf-8")
    assert "buildPythonApplication" in flake_text
    assert "pyside6" in flake_text
    assert "psutil" in flake_text
    assert "nixosModules" in flake_text
    assert "homeManagerModules" in flake_text

    default_text = default_nix.read_text(encoding="utf-8")
    assert "buildPythonApplication" in default_text
    assert "wrapQtAppsHook" in default_text


def test_installer_cli_dry_run_and_help():
    """Verify installer responds to --help and --dry-run without modifying state."""
    repo_root = Path(__file__).resolve().parent.parent
    install_sh = repo_root / "install.sh"

    res_help = subprocess.run([str(install_sh), "--help"], capture_output=True, text=True, check=False)
    assert res_help.returncode == 0
    assert "--install-deps" in res_help.stdout
    assert "--dry-run" in res_help.stdout

    res_dry = subprocess.run([str(install_sh), "--dry-run"], capture_output=True, text=True, check=False)
    assert res_dry.returncode == 0
    assert "Dry run mode: exiting without changes" in res_dry.stdout


def test_uninstaller_cli_dry_run_and_purge():
    """Verify uninstaller supports --purge, --dry-run, and --help."""
    repo_root = Path(__file__).resolve().parent.parent
    uninstall_sh = repo_root / "uninstall.sh"

    res_help = subprocess.run([str(uninstall_sh), "--help"], capture_output=True, text=True, check=False)
    assert res_help.returncode == 0
    assert "--purge" in res_help.stdout

    res_dry = subprocess.run([str(uninstall_sh), "--dry-run", "--purge"], capture_output=True, text=True, check=False)
    assert res_dry.returncode == 0
    assert "Mode: FULL PURGE" in res_dry.stdout
    assert "Dry-run mode active" in res_dry.stdout
