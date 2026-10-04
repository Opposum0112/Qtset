from __future__ import annotations

import json
from pathlib import Path

from qtile_settings.adapters import themes


def test_list_themes_with_dir(tmp_path: Path, monkeypatch):
    themes_dir = tmp_path / "themes"
    themes_dir.mkdir()
    (themes_dir / "catppuccin-mocha.json").write_text("{}", encoding="utf-8")
    (themes_dir / "gruvbox-dark.json").write_text("{}", encoding="utf-8")
    (themes_dir / "current_theme.json").write_text("{}", encoding="utf-8")  # should be excluded

    monkeypatch.setattr(themes, "THEMES_DIR", themes_dir)
    found = themes.list_themes()
    assert "catppuccin-mocha" in found
    assert "gruvbox-dark" in found
    assert "current_theme" not in found


def test_list_themes_fallback(tmp_path: Path, monkeypatch):
    nonexistent = tmp_path / "no_themes"
    monkeypatch.setattr(themes, "THEMES_DIR", nonexistent)
    fallback = themes.list_themes()
    assert "catppuccin-mocha" in fallback
    assert len(fallback) > 1


def test_get_current_theme_name(tmp_path: Path, monkeypatch):
    current_file = tmp_path / "current_theme.json"
    current_file.write_text(json.dumps({"name": "gruvbox-dark"}), encoding="utf-8")
    monkeypatch.setattr(themes, "CURRENT_THEME_FILE", current_file)

    assert themes.get_current_theme_name() == "gruvbox-dark"


def test_get_theme_palette(tmp_path: Path, monkeypatch):
    themes_dir = tmp_path / "themes"
    themes_dir.mkdir()
    sample = {
        "name": "custom",
        "colors": {
            "base": "#000000",
            "mauve": "#ff00ff",
        },
    }
    (themes_dir / "custom.json").write_text(json.dumps(sample), encoding="utf-8")
    monkeypatch.setattr(themes, "THEMES_DIR", themes_dir)

    pal = themes.get_theme_palette("custom")
    assert pal["base"] == "#000000"
    assert pal["mauve"] == "#ff00ff"
    assert "text" in pal  # merged with DEFAULT_PALETTE


def test_apply_theme_fallback_writes_current_theme(tmp_path: Path, monkeypatch):
    themes_dir = tmp_path / "themes"
    themes_dir.mkdir()
    (themes_dir / "solarized-dark.json").write_text(json.dumps({"name": "solarized-dark"}), encoding="utf-8")
    current_file = themes_dir / "current_theme.json"

    monkeypatch.setattr(themes, "THEMES_DIR", themes_dir)
    monkeypatch.setattr(themes, "CURRENT_THEME_FILE", current_file)
    monkeypatch.setattr(themes, "APPLY_THEME_BIN", tmp_path / "nonexistent-script")

    ok, _ = themes.apply_theme("solarized-dark")
    assert ok
    assert current_file.is_file()
    assert json.loads(current_file.read_text(encoding="utf-8"))["name"] == "solarized-dark"


def test_get_current_theme_palette(tmp_path: Path, monkeypatch):
    current_file = tmp_path / "current_theme.json"
    current_file.write_text(
        json.dumps({
            "name": "gruvbox-dark",
            "colors": {
                "base": "#282828",
                "mantle": "#1d2021",
                "text": "#ebdbb2",
            },
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(themes, "CURRENT_THEME_FILE", current_file)

    pal = themes.get_current_theme_palette()
    assert pal["base"] == "#282828"
    assert pal["mantle"] == "#1d2021"
    assert pal["text"] == "#ebdbb2"


def test_resolve_theme_colors_semantic_mapping():
    from qtile_settings.theme import resolve_theme_colors

    gruvbox_palette = {
        "base": "#282828",
        "mantle": "#1d2021",
        "crust": "#141617",
        "surface0": "#32302f",
        "surface1": "#3c3836",
        "surface2": "#504945",
        "text": "#ebdbb2",
        "overlay": "#928374",
    }
    resolved = resolve_theme_colors(gruvbox_palette)
    assert resolved["surface"] == "#1d2021"  # mapped from mantle
    assert resolved["surfaceContainer"] == "#282828"  # mapped from base
    assert resolved["surfaceContainerHigh"] == "#32302f"  # mapped from surface0
    assert resolved["outline"] == "#504945"  # mapped from surface2
    assert resolved["text"] == "#ebdbb2"
    assert resolved["muted"] == "#928374"

