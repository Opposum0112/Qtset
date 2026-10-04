from __future__ import annotations

import json
from pathlib import Path

from qtile_settings.adapters import system


def test_system_summary():
    data = system.system_summary()
    assert "hostname" in data
    assert "os" in data
    assert "memory_percent" in data
    assert "cpu_percent" in data


def test_ansi_to_html():
    raw_ansi = "\x1b[38;2;203;166;247mTest\x1b[0m \x1b[1;38;2;255;0;0mBoldRed\x1b[0m"
    html = system.ansi_to_html(raw_ansi)
    assert "<pre" in html
    assert 'style="color: rgb(203, 166, 247);"' in html
    assert 'style="color: rgb(255, 0, 0); font-weight: bold;"' in html
    assert "Test" in html
    assert "BoldRed" in html


def test_get_fastfetch_qtile_logo_html_default():
    html = system.get_fastfetch_qtile_logo_html()
    assert "<pre" in html
    assert "QTILE" in html
    assert "rgb(203, 166, 247)" in html


def test_get_fastfetch_qtile_logo_html_custom(tmp_path: Path):
    cfg_file = tmp_path / "config.jsonc"
    custom_content = {
        "logo": {
            "type": "data",
            "source": "\x1b[38;2;100;200;250mCUSTOM_LOGO\x1b[0m",
        }
    }
    cfg_file.write_text(json.dumps(custom_content), encoding="utf-8")
    html = system.get_fastfetch_qtile_logo_html(cfg_file)
    assert "CUSTOM_LOGO" in html
    assert "rgb(100, 200, 250)" in html


def test_get_fastfetch_qtile_logo_html_fallback(tmp_path: Path):
    nonexistent = tmp_path / "nonexistent.jsonc"
    html = system.get_fastfetch_qtile_logo_html(nonexistent)
    assert "QTILE" in html
    assert "<pre" in html
