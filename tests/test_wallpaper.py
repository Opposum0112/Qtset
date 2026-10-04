"""Unit tests for the wallpaper discovery and background application adapter."""

from __future__ import annotations

from pathlib import Path

from qtile_settings.adapters import wallpaper


def test_list_wallpapers(tmp_path: Path):
    """Verify that only supported image formats (.jpg, .png, .webp) are discovered."""
    (tmp_path / "wp1.jpg").write_text("dummy", encoding="utf-8")
    (tmp_path / "wp2.PNG").write_text("dummy", encoding="utf-8")
    (tmp_path / "wp3.webp").write_text("dummy", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("dummy", encoding="utf-8")

    files = wallpaper.list_wallpapers(tmp_path)
    names = [p.name for p in files]
    assert "wp1.jpg" in names
    assert "wp2.PNG" in names
    assert "wp3.webp" in names
    assert "notes.txt" not in names


def test_set_wallpaper_nonexistent_file():
    """Verify that attempting to set a non-existent wallpaper path fails gracefully."""
    ok, err = wallpaper.set_wallpaper("/nonexistent/path/to/wallpaper.jpg")
    assert not ok
    assert "not found" in err.lower()
