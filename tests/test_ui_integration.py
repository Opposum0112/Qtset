from __future__ import annotations

import os
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication, QScrollArea

from qtile_settings.theme import apply_theme
from qtile_settings.ui.config_page import QtileConfigPage
from qtile_settings.ui.main_window import MainWindow
from qtile_settings.ui.pages import HardwarePage, OverviewPage, ThemePage
from qtile_settings.ui.quick_settings import QuickSettings


@pytest.fixture(scope="session")
def qapp():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    apply_theme(app)
    return app


def test_main_window_pages_instantiation(qapp):
    win = MainWindow()
    assert win.sidebar.count() == 7
    assert win.stack.count() == 7

    # Verify switching pages
    for i in range(win.sidebar.count()):
        win.sidebar.setCurrentRow(i)
        assert win.stack.currentIndex() == i


def test_quick_settings_instantiation(qapp):
    qs = QuickSettings()
    assert qs.windowTitle() == "Quick Settings"
    assert qs.volume.maximum() == 150
    qs.refresh_audio()
    qs.quick_reload_qtile()
    assert "Reload" in qs.status.text()


def test_overview_page_log_toggle(qapp):
    page = OverviewPage()
    assert "QTILE" in page.logo_label.text()
    assert "<pre" in page.logo_label.text()
    assert len(page.chip_layout.text()) > 2
    assert len(page.chip_theme.text()) > 2
    assert page.log_frame.isHidden()
    page.toggle_log()
    assert not page.log_frame.isHidden()
    page.toggle_log()
    assert page.log_frame.isHidden()




def test_theme_page_preview(qapp):
    page = ThemePage()
    page.preview_theme()
    assert "■ base" in page.palette_preview.text()


def test_hardware_page_audio_change(qapp):
    page = HardwarePage()
    page.change_volume(75)
    assert page.volume_slider.value() >= 0


def test_network_page_render(qapp):
    from qtile_settings.ui.pages import NetworkPage
    page = NetworkPage()
    assert page.wifi_table.columnCount() == 5
    assert page.iface_table.columnCount() == 4
    page.refresh()


def test_keybindings_page_filter(qapp):
    from qtile_settings.ui.keybindings_page import KeybindingsPage
    page = KeybindingsPage()
    assert page.table.columnCount() == 5
    page.search_input.setText("Return")
    assert len(page.filtered_items) >= 1
    page.cat_filter.setCurrentText("Applications & Launchers")
    assert len(page.filtered_items) >= 1


def test_qtile_config_page_auto_save(qapp, monkeypatch):
    saved_prefs = {}
    monkeypatch.setattr(
        "qtile_settings.adapters.configuration.save_preference",
        lambda k, v: saved_prefs.update({k: v}),
    )
    monkeypatch.setattr(
        "qtile_settings.adapters.qtile.reload_qtile",
        lambda: (True, "Reloaded"),
    )

    page = QtileConfigPage()
    assert page.tabs.count() == 6

    # Test slider update triggers auto-save
    page._queue_update("GAP", 16, immediate=True)
    assert saved_prefs.get("GAP") == 16
    assert "Auto-saved" in page.sync_status.text()

    # Test toggle triggers auto-save
    page._queue_update("follow_mouse_focus", False, immediate=True)
    assert saved_prefs.get("follow_mouse_focus") is False


def test_qtile_config_page_undo(qapp, monkeypatch):
    saved_prefs = {}
    monkeypatch.setattr(
        "qtile_settings.adapters.configuration.save_preference",
        lambda k, v: saved_prefs.update({k: v}),
    )
    monkeypatch.setattr(
        "qtile_settings.adapters.qtile.reload_qtile",
        lambda: (True, "Reloaded"),
    )

    page = QtileConfigPage()
    assert page.btn_undo.isEnabled() is False

    orig_gap = int(page._current_values.get("GAP", 4))
    # Change GAP
    page._queue_update("GAP", 32, immediate=True)
    assert page.btn_undo.isEnabled() is True
    assert saved_prefs.get("GAP") == 32

    # Click Undo
    page.undo_last_change()
    assert saved_prefs.get("GAP") == orig_gap
    assert page.gap_slider.value() == orig_gap
    assert page.btn_undo.isEnabled() is False
    assert "Undid" in page.sync_status.text()


def test_backups_dialog_instantiation(qapp, monkeypatch):
    from qtile_settings.ui.config_page import BackupsDialog
    monkeypatch.setattr(
        "qtile_settings.adapters.configuration.list_backups",
        lambda: [{
            "path": Path("/tmp/settings.py.backup.1"),
            "filename": "settings.py.backup.1",
            "target_name": "settings.py",
            "timestamp": "20261003-120000",
            "size_bytes": 1024,
            "mtime": 123456789,
        }],
    )
    dialog = BackupsDialog()
    assert dialog.table.rowCount() == 1
    assert dialog.table.item(0, 0).text() == "settings.py"


def test_tools_page_diagnostic_render(qapp):
    from qtile_settings.ui.pages import ToolsPage
    page = ToolsPage()
    assert page.findChild(QScrollArea) is not None
    assert page.cards_layout.count() == 2
    # Verify diagnostic refresh runs without errors
    page.refresh()
    assert page.cards_layout.count() == 2


