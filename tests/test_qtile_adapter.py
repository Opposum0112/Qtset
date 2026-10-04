from __future__ import annotations

from pathlib import Path

from qtile_settings.adapters import commands, qtile


def test_config_path_returns_path():
    path = qtile.config_path()
    assert isinstance(path, Path)
    assert path.name == "config.py"


def test_get_qtile_log_nonexistent(tmp_path: Path, monkeypatch):
    nonexistent = tmp_path / "qtile.log"
    monkeypatch.setattr(qtile, "LOG_FILE", nonexistent)
    text = qtile.get_qtile_log()
    assert "not found" in text.lower()


def test_get_qtile_log_reads_tail(tmp_path: Path, monkeypatch):
    log_file = tmp_path / "qtile.log"
    log_file.write_text("\n".join(f"Line {i}" for i in range(100)), encoding="utf-8")
    monkeypatch.setattr(qtile, "LOG_FILE", log_file)

    tail = qtile.get_qtile_log(max_lines=10)
    lines = tail.splitlines()
    assert len(lines) == 10
    assert lines[-1] == "Line 99"
    assert lines[0] == "Line 90"


def test_check_config_nonexistent(tmp_path: Path, monkeypatch):
    nonexistent = tmp_path / "config.py"
    monkeypatch.setattr(qtile, "CONFIG_FILE", nonexistent)
    ok, msg = qtile.check_config()
    assert not ok
    assert "not found" in msg


def test_reload_qtile_handles_missing_cli(monkeypatch):
    # If qtile is not on path or mocked, run_command returns not ok
    monkeypatch.setattr(
        qtile,
        "run_command",
        lambda argv, **kwargs: commands.CommandResult(False, error="Mocked missing CLI"),
    )
    ok, msg = qtile.reload_qtile()
    assert not ok
    assert "Mocked" in msg


def test_get_current_layout_from_cache(tmp_path: Path, monkeypatch):
    cache_file = tmp_path / "qtile-current-layout"
    cache_file.write_text("MonadTall\n", encoding="utf-8")
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    # create .cache subdir
    dot_cache = tmp_path / ".cache"
    dot_cache.mkdir(parents=True, exist_ok=True)
    (dot_cache / "qtile-current-layout").write_text("MonadTall\n", encoding="utf-8")

    layout = qtile.get_current_layout()
    assert layout == "MonadTall"


def test_get_current_layout_fallback(tmp_path: Path, monkeypatch):
    empty_home = tmp_path / "empty"
    empty_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: empty_home)
    layout = qtile.get_current_layout()
    assert layout == "Niri Scroller Ribbon"

