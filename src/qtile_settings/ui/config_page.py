"""Qtile configuration and desktop preferences view.

Provides a 6-tab settings management interface (Dimensions & Fonts, Window Behavior,
Environment & Launchers, Workspace Layouts, Autostart Daemons, Modular Config Files),
featuring interactive undo history stack, restore defaults, and backup restoration dialogs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from qtile_settings.adapters import commands, configuration, qtile
from qtile_settings.ui.common import (
    ActionSettingRow,
    SelectionSettingRow,
    SliderSettingRow,
    StringSettingRow,
    ToggleSettingRow,
    card,
    create_pill_badge,
)


class BackupsDialog(QDialog):
    """Dialog to inspect and restore timestamped configuration backups."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Configuration Backups")
        self.setMinimumWidth(680)
        self.setMinimumHeight(380)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        heading = QLabel("Saved Configuration Backups")
        heading.setObjectName("SectionTitle")
        layout.addWidget(heading)

        sub = QLabel("Backups are automatically created whenever configuration files or settings are modified.")
        sub.setObjectName("Muted")
        layout.addWidget(sub)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Target File", "Timestamp", "Size", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 160)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 90)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, 115)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(True)
        layout.addWidget(self.table, 1)

        self.btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.btn_box.rejected.connect(self.reject)
        layout.addWidget(self.btn_box)

        self.refresh_backups()

    def refresh_backups(self):
        backups = configuration.list_backups()
        self.table.setRowCount(len(backups))
        for row, b in enumerate(backups):
            target_item = QTableWidgetItem(b["target_name"])
            target_item.setFlags(target_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            target_item.setForeground(QColor("#89b4fa"))
            self.table.setItem(row, 0, target_item)

            stamp_item = QTableWidgetItem(b["timestamp"])
            stamp_item.setFlags(stamp_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            stamp_item.setForeground(QColor("#cdd6f4"))
            self.table.setItem(row, 1, stamp_item)

            size_str = f"{b['size_bytes'] / 1024:.1f} KB" if b['size_bytes'] >= 1024 else f"{b['size_bytes']} B"
            size_item = QTableWidgetItem(size_str)
            size_item.setFlags(size_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            size_item.setForeground(QColor("#a6adc8"))
            self.table.setItem(row, 2, size_item)

            btn_restore = QPushButton("󰑐 Restore")
            btn_restore.setStyleSheet("padding: 4px 12px; font-size: 8.5pt; font-weight: 600;")
            btn_restore.clicked.connect(lambda _, path=b["path"], name=b["target_name"], ts=b["timestamp"]: self.restore(path, name, ts))
            self.table.setCellWidget(row, 3, btn_restore)

    def restore(self, path: Path, target_name: str, timestamp: str):
        reply = QMessageBox.question(
            self,
            "Confirm Restore",
            f"Restore '{target_name}' from backup timestamped '{timestamp}'?\nA backup of the current file will be created first.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            ok, msg = configuration.restore_backup(path)
            if ok:
                QMessageBox.information(self, "Restore Successful", msg)
                self.accept()
            else:
                QMessageBox.critical(self, "Restore Failed", msg)


class QtileConfigPage(QWidget):
    """Comprehensive Material 3 settings manager for the Qtile-Con environment."""

    def __init__(self):
        super().__init__()
        self._widgets: dict[str, Any] = {}
        self._undo_stack: list[tuple[str, Any, Any]] = []
        self._is_undoing: bool = False
        self._current_values: dict[str, Any] = configuration.read_all_preferences()

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(12)

        # Header Title & Description
        header_layout = QVBoxLayout()
        header_layout.setSpacing(8)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title = QLabel("Qtile Desktop Preferences")
        title.setObjectName("PageTitle")
        title.setWordWrap(True)
        title_col.addWidget(title)

        desc = QLabel("Configure all desktop dimensions, window behaviors, workspace layouts, autostart daemons, and modular files.")
        desc.setObjectName("Muted")
        desc.setWordWrap(True)
        title_col.addWidget(desc)
        header_layout.addLayout(title_col)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.btn_undo = QPushButton("󰕌 Undo")
        self.btn_undo.setEnabled(False)
        self.btn_undo.setToolTip("Revert the most recent configuration change")
        self.btn_undo.clicked.connect(self.undo_last_change)
        toolbar.addWidget(self.btn_undo)

        self.btn_defaults = QPushButton("󰑐 Defaults")
        self.btn_defaults.setToolTip("Reset all desktop preferences to factory defaults")
        self.btn_defaults.clicked.connect(self.restore_factory_defaults)
        toolbar.addWidget(self.btn_defaults)

        self.btn_backups = QPushButton("󰋚 Backups")
        self.btn_backups.setToolTip("View and restore timestamped configuration backups")
        self.btn_backups.clicked.connect(self.open_backups_dialog)
        toolbar.addWidget(self.btn_backups)

        self.auto_reload_cb = QCheckBox("Auto-reload Qtile on save")
        self.auto_reload_cb.setChecked(True)
        self.auto_reload_cb.setStyleSheet("font-weight: 600; color: #89b4fa;")
        toolbar.addWidget(self.auto_reload_cb)

        toolbar.addStretch()

        self.sync_status = QLabel("● Ready · Changes auto-save")
        self.sync_status.setStyleSheet("color: #a6e3a1; font-weight: 600; font-size: 9pt;")
        toolbar.addWidget(self.sync_status)

        header_layout.addLayout(toolbar)
        root.addLayout(header_layout)

        # Debounce timer for sliders and rapid inputs
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(350)
        self._debounce_timer.timeout.connect(self._flush_auto_save)
        self._pending_updates: dict[str, Any] = {}

        # Tabbed configuration panels
        self.tabs = QTabWidget()
        self.tabs.addTab(self._dimensions_tab(), "󰖰  Dimensions & Fonts")
        self.tabs.addTab(self._behavior_tab(), "󰘳  Window Behavior")
        self.tabs.addTab(self._environment_tab(), "󰀻  Environment & Launchers")
        self.tabs.addTab(self._workspaces_tab(), "󰮯  Workspace Layouts")
        self.tabs.addTab(self._autostart_tab(), "󰒋  Autostart Daemons")
        self.tabs.addTab(self._editor_tab(), "󰈔  Config Files Editor")
        root.addWidget(self.tabs, 1)

    def _wrap_in_scroll(self, content_widget: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(content_widget)
        return scroll

    def _queue_update(self, key: str, value: Any, immediate: bool = False):
        if not self._is_undoing:
            old_val = self._current_values.get(key)
            if old_val is not None and old_val != value:
                self._undo_stack.append((key, old_val, value))
                self.btn_undo.setEnabled(True)
                self._current_values[key] = value

        self._pending_updates[key] = value
        self.sync_status.setText("● Saving changes...")
        self.sync_status.setStyleSheet("color: #f9e2af; font-weight: 600; font-size: 9pt;")
        if immediate:
            self._debounce_timer.stop()
            self._flush_auto_save()
        else:
            self._debounce_timer.start()

    def _flush_auto_save(self):
        if not self._pending_updates:
            return
        items = dict(self._pending_updates)
        self._pending_updates.clear()
        try:
            for k, v in items.items():
                configuration.save_preference(k, v)
            self.sync_status.setText("● Auto-saved successfully")
            self.sync_status.setStyleSheet("color: #a6e3a1; font-weight: 600; font-size: 9pt;")

            if self.auto_reload_cb.isChecked():
                qtile.reload_qtile()
        except (OSError, ValueError, SyntaxError, KeyError) as exc:
            self.sync_status.setText(f"● Save error: {exc}")
            self.sync_status.setStyleSheet("color: #f38ba8; font-weight: 600; font-size: 9pt;")

    def undo_last_change(self):
        """Undo the most recent configuration change and update the UI."""
        if not self._undo_stack:
            return
        key, old_val, _ = self._undo_stack.pop()
        self.btn_undo.setEnabled(len(self._undo_stack) > 0)

        self._is_undoing = True
        try:
            widget = self._widgets.get(key)
            if isinstance(widget, SliderSettingRow):
                widget.setValue(int(old_val))
            elif isinstance(widget, ToggleSettingRow):
                widget.setChecked(bool(old_val))
            elif isinstance(widget, SelectionSettingRow):
                widget.setValue(old_val)
            elif isinstance(widget, StringSettingRow):
                widget.setText(str(old_val))

            configuration.save_preference(key, old_val)
            self._current_values[key] = old_val

            self.sync_status.setText(f"● Undid: {key} -> {old_val}")
            self.sync_status.setStyleSheet("color: #a6e3a1; font-weight: 600; font-size: 9pt;")

            if self.auto_reload_cb.isChecked():
                qtile.reload_qtile()
        except (OSError, ValueError, SyntaxError, KeyError) as exc:
            self.sync_status.setText(f"● Undo error: {exc}")
            self.sync_status.setStyleSheet("color: #f38ba8; font-weight: 600; font-size: 9pt;")
        finally:
            self._is_undoing = False

    def restore_factory_defaults(self):
        """Reset all preferences to factory defaults after confirmation."""
        reply = QMessageBox.question(
            self,
            "Restore Defaults",
            "Are you sure you want to reset all Qtile preferences to factory defaults?\nA backup will be created first.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        ok, msg = configuration.restore_defaults()
        if not ok:
            QMessageBox.critical(self, "Restore Error", msg)
            return

        self._undo_stack.clear()
        self.btn_undo.setEnabled(False)
        self.reload_all_ui()
        if self.auto_reload_cb.isChecked():
            qtile.reload_qtile()
        QMessageBox.information(self, "Defaults Restored", "All desktop preferences have been reset to factory defaults.")

    def open_backups_dialog(self):
        """Open the backups browser dialog and reload UI if a backup was restored."""
        dialog = BackupsDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.reload_all_ui()
            if self.auto_reload_cb.isChecked():
                qtile.reload_qtile()

    def reload_all_ui(self):
        """Re-read configuration and reload all UI widgets."""
        self._is_undoing = True
        try:
            prefs = configuration.read_all_preferences()
            self._current_values = dict(prefs)
            for key, val in prefs.items():
                widget = self._widgets.get(key)
                if isinstance(widget, SliderSettingRow):
                    widget.setValue(int(val))
                elif isinstance(widget, ToggleSettingRow):
                    widget.setChecked(bool(val))
                elif isinstance(widget, SelectionSettingRow):
                    widget.setValue(val)
                elif isinstance(widget, StringSettingRow):
                    widget.setText(str(val))
            if hasattr(self, "file_editor"):
                self._load_selected_file()
            self.sync_status.setText("● Configuration reloaded")
            self.sync_status.setStyleSheet("color: #a6e3a1; font-weight: 600; font-size: 9pt;")
        finally:
            self._is_undoing = False

    # --------------------------------------------------------------------------
    # Tab 1: Dimensions & Typography
    # --------------------------------------------------------------------------
    def _dimensions_tab(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(14)
        layout.setContentsMargins(8, 8, 8, 8)

        prefs = configuration.read_all_preferences()

        frame, box = card("Window Geometry & Margins", "Pixel spacing, outer gaps, and window borders", icon="󰖰")
        self.gap_slider = SliderSettingRow(
            "Outer Window Gap", 0, 48, int(prefs.get("GAP", 4)), unit="px",
            description="Spacing margin between tiled windows and desktop screen edges",
            icon="󰖰", on_change=lambda v: self._queue_update("GAP", v)
        )
        self._widgets["GAP"] = self.gap_slider
        box.addWidget(self.gap_slider)

        self.border_slider = SliderSettingRow(
            "Border Width", 0, 16, int(prefs.get("BORDER_WIDTH", 2)), unit="px",
            description="Thickness of active and inactive client window borders",
            icon="󰒓", on_change=lambda v: self._queue_update("BORDER_WIDTH", v)
        )
        self._widgets["BORDER_WIDTH"] = self.border_slider
        box.addWidget(self.border_slider)

        self.bar_slider = SliderSettingRow(
            "Status Bar Height", 20, 80, int(prefs.get("BAR_HEIGHT", 36)), unit="px",
            description="Total pixel height of the top Qtile status bar",
            icon="󰍹", on_change=lambda v: self._queue_update("BAR_HEIGHT", v)
        )
        self._widgets["BAR_HEIGHT"] = self.bar_slider
        box.addWidget(self.bar_slider)
        layout.addWidget(frame)

        frame, box = card("Typography & Font Scale", "Font families and size for status bar widgets, tags, and titles", icon="󰛄")
        common_fonts = [
            "JetBrainsMono Nerd Font",
            "FiraCode Nerd Font",
            "Hack Nerd Font",
            "Noto Sans Mono",
            "Monospace",
        ]
        curr_font = str(prefs.get("FONT", "JetBrainsMono Nerd Font"))
        if curr_font not in common_fonts:
            common_fonts.insert(0, curr_font)

        self.font_row = SelectionSettingRow(
            "Font Family",
            options=common_fonts,
            current_val=curr_font,
            description="Active Nerd Font used across all bar widgets and text capsules",
            icon="󰬴",
            on_change=lambda f: self._queue_update("FONT", f, immediate=True)
        )
        self._widgets["FONT"] = self.font_row
        box.addWidget(self.font_row)

        self.font_size_slider = SliderSettingRow(
            "Font Size", 8, 28, int(prefs.get("FONT_SIZE", 12)), unit="pt",
            description="Default text scale in points for status bar indicators and menus",
            icon="󰬴", on_change=lambda v: self._queue_update("FONT_SIZE", v)
        )
        self._widgets["FONT_SIZE"] = self.font_size_slider
        box.addWidget(self.font_size_slider)
        layout.addWidget(frame)

        layout.addStretch()
        return self._wrap_in_scroll(content)

    # --------------------------------------------------------------------------
    # Tab 2: Window Manager Behaviors
    # --------------------------------------------------------------------------
    def _behavior_tab(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(14)
        layout.setContentsMargins(8, 8, 8, 8)

        prefs = configuration.read_all_preferences()

        frame, box = card("Focus & Pointer Policies", "Dynamic mouse focus and cursor movement behaviors", icon="󰍽")
        self.focus_toggle = ToggleSettingRow(
            "Focus Follows Mouse Cursor",
            "Window focus dynamically shifts as the mouse pointer moves over client windows",
            checked=bool(prefs.get("follow_mouse_focus", True)),
            icon="󰍽",
            on_toggle=lambda c: self._queue_update("follow_mouse_focus", c, immediate=True)
        )
        self._widgets["follow_mouse_focus"] = self.focus_toggle
        box.addWidget(self.focus_toggle)

        self.bring_front_toggle = ToggleSettingRow(
            "Bring Floating Windows to Front on Click",
            "Clicking anywhere on a floating window automatically raises it above all tiled windows",
            checked=bool(prefs.get("bring_front_click", True)),
            icon="󰘸",
            on_toggle=lambda c: self._queue_update("bring_front_click", c, immediate=True)
        )
        self._widgets["bring_front_click"] = self.bring_front_toggle
        box.addWidget(self.bring_front_toggle)

        self.cursor_warp_toggle = ToggleSettingRow(
            "Cursor Warp on Focus Change",
            "Automatically jump the mouse pointer to the center of the newly focused window",
            checked=bool(prefs.get("cursor_warp", False)),
            icon="󰆾",
            on_toggle=lambda c: self._queue_update("cursor_warp", c, immediate=True)
        )
        self._widgets["cursor_warp"] = self.cursor_warp_toggle
        box.addWidget(self.cursor_warp_toggle)
        layout.addWidget(frame)

        frame, box = card("Window Lifecycle & Compatibility", "Fullscreen handling and X11 window manager identification", icon="󰊓")
        self.auto_fullscreen_toggle = ToggleSettingRow(
            "Auto-Fullscreen Application Requests",
            "Automatically grant fullscreen mode when requested by video players and games",
            checked=bool(prefs.get("auto_fullscreen", True)),
            icon="󰊓",
            on_toggle=lambda c: self._queue_update("auto_fullscreen", c, immediate=True)
        )
        self._widgets["auto_fullscreen"] = self.auto_fullscreen_toggle
        box.addWidget(self.auto_fullscreen_toggle)

        self.activation_row = SelectionSettingRow(
            "Window Activation Policy",
            options=["smart", "urgent", "focus", "never"],
            current_val=str(prefs.get("focus_on_window_activation", "smart")),
            description="Policy when background applications request desktop focus (smart is recommended)",
            icon="󰌌",
            on_change=lambda t: self._queue_update("focus_on_window_activation", t, immediate=True)
        )
        self._widgets["focus_on_window_activation"] = self.activation_row
        box.addWidget(self.activation_row)

        self.wmname_row = StringSettingRow(
            "Window Manager Name (wmname)",
            current_val=str(prefs.get("wmname", "LG3D")),
            placeholder="LG3D",
            description="Reported WM identifier (LG3D fixes Java AWT/Swing graphical rendering glitches)",
            icon="󰒓",
            on_change=lambda t: self._queue_update("wmname", t, immediate=True)
        )
        self._widgets["wmname"] = self.wmname_row
        box.addWidget(self.wmname_row)
        layout.addWidget(frame)

        layout.addStretch()
        return self._wrap_in_scroll(content)

    # --------------------------------------------------------------------------
    # Tab 3: Environment & Launchers
    # --------------------------------------------------------------------------
    def _environment_tab(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(14)
        layout.setContentsMargins(8, 8, 8, 8)

        prefs = configuration.read_all_preferences()

        frame, box = card("Core Modifiers & Terminal", "Primary modifier keys and default terminal emulator", icon="󰌌")
        self.mod_row = SelectionSettingRow(
            "Primary Modifier Key (MOD)",
            options=[("mod4 (Super / Command / Windows)", "mod4"), ("mod1 (Alt / Option)", "mod1")],
            current_val=str(prefs.get("MOD", "mod4")),
            description="Primary modifier for all Qtile shortcuts (Super is tuned for Mac ergonomics)",
            icon="󰘳",
            on_change=lambda m: self._queue_update("MOD", m, immediate=True)
        )
        self._widgets["MOD"] = self.mod_row
        box.addWidget(self.mod_row)

        curr_term = str(prefs.get("TERMINAL", "kitty"))
        term_options = ["kitty", "alacritty", "xterm", "foot", "wezterm"]
        if curr_term not in term_options:
            term_options.insert(0, curr_term)

        self.terminal_row = SelectionSettingRow(
            "Default Terminal Emulator",
            options=term_options,
            current_val=curr_term,
            description="Terminal launched with Super + Enter and used by terminal tools",
            icon="󰆍",
            on_change=lambda t: self._queue_update("TERMINAL", t, immediate=True)
        )
        self._widgets["TERMINAL"] = self.terminal_row
        box.addWidget(self.terminal_row)

        box.addWidget(ActionSettingRow(
            "Test Terminal Launch",
            button_label="󰑐 Launch Terminal",
            description="Verify that the currently selected terminal emulator launches correctly",
            icon="󰆍",
            on_click=lambda: commands.run_command([str(prefs.get("TERMINAL", "kitty"))])
        ))
        layout.addWidget(frame)

        frame, box = card("Application Launchers & Wallpapers", "Rofi launcher configuration and wallpaper directory", icon="󰀻")
        self.launcher_row = StringSettingRow(
            "Application Launcher Command",
            current_val=str(prefs.get("LAUNCHER", "rofi -show combi")),
            placeholder="rofi command string",
            description="Command executed when pressing Super + d",
            icon="󰀻",
            on_change=lambda t: self._queue_update("LAUNCHER", t, immediate=False)
        )
        self._widgets["LAUNCHER"] = self.launcher_row
        box.addWidget(self.launcher_row)

        self.wallpaper_row = StringSettingRow(
            "Wallpaper Collection Directory",
            current_val=str(prefs.get("WALLPAPER_DIR", "~/Pictures/Wallpapers")),
            placeholder="~/Pictures/Wallpapers",
            description="Folder scanned for desktop wallpapers by set-wallpaper and Theme settings",
            icon="󰸉",
            browse_dir=True,
            on_change=lambda t: self._queue_update("WALLPAPER_DIR", t, immediate=True)
        )
        self._widgets["WALLPAPER_DIR"] = self.wallpaper_row
        box.addWidget(self.wallpaper_row)
        layout.addWidget(frame)

        layout.addStretch()
        return self._wrap_in_scroll(content)

    # --------------------------------------------------------------------------
    # Tab 4: Workspace Layouts
    # --------------------------------------------------------------------------
    def _workspaces_tab(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(14)
        layout.setContentsMargins(8, 8, 8, 8)

        frame, box = card(
            "Per-Workspace Independent Layouts",
            "Each workspace in Qtile-Con maintains an isolated default layout without cross-workspace leakage.",
            icon="󰮯"
        )

        workspace_names = [
            ("1", "󰈹", "Browsers"),
            ("2", "󰆍", "Terminals"),
            ("3", "󰖟", "Code & IDEs"),
            ("4", "󰙯", "Chat & Discord"),
            ("5", "󰎆", "Music & Media"),
            ("6", "󰓓", "Gaming & Steam"),
            ("7", "󰒓", "System Tools"),
            ("8", "󰉋", "File Managers"),
            ("9", "󰐃", "Graphics & Design"),
        ]

        self.ws_layouts = configuration.read_workspace_layouts()

        for tag, icon, role in workspace_names:
            curr_l = self.ws_layouts.get(tag, "columns")
            row = SelectionSettingRow(
                f"Workspace {tag} ({icon} {role})",
                options=configuration.AVAILABLE_LAYOUTS,
                current_val=curr_l,
                description=f"Default tiling layout when switching to workspace tag {tag}",
                icon=icon,
                on_change=lambda l, t=tag: self._update_workspace_layout(t, l)
            )
            box.addWidget(row)

        layout.addWidget(frame)
        layout.addStretch()
        return self._wrap_in_scroll(content)

    def _update_workspace_layout(self, tag: str, layout_name: str):
        self.ws_layouts[tag] = layout_name
        configuration.save_workspace_layouts(self.ws_layouts)
        self.sync_status.setText(f"● Workspace {tag} layout set to {layout_name}")
        self.sync_status.setStyleSheet("color: #a6e3a1; font-weight: 600; font-size: 9pt;")
        if self.auto_reload_cb.isChecked():
            qtile.reload_qtile()

    # --------------------------------------------------------------------------
    # Tab 5: Autostart Daemons
    # --------------------------------------------------------------------------
    def _autostart_tab(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(14)
        layout.setContentsMargins(8, 8, 8, 8)

        frame, box = card(
            "Session Startup Daemons",
            "Status and management of core background daemons initialized in scripts/autostart.",
            icon="󰒋"
        )

        services = configuration.get_autostart_services_status()
        for svc in services:
            proc = svc["process"]
            label = svc["label"]
            icon = svc["icon"]
            running = svc["running"]

            row_frame = QFrame()
            row_frame.setObjectName("SettingRow")
            row_layout = QHBoxLayout(row_frame)
            row_layout.setContentsMargins(4, 6, 4, 6)

            # Left badge & description
            row_layout.addWidget(QLabel(f"<span style='font-size: 13pt; color: #89b4fa;'>{icon}</span>"))

            text_col = QVBoxLayout()
            text_col.setSpacing(2)
            title_lbl = QLabel(f"<b>{label}</b> (<code>{proc}</code>)")
            text_col.addWidget(title_lbl)
            cmd_lbl = QLabel(f"Command: {svc['command']}")
            cmd_lbl.setObjectName("Muted")
            text_col.addWidget(cmd_lbl)
            row_layout.addLayout(text_col, 1)

            # Running status pill
            status_text = "Running" if running else "Stopped"
            status_color = "#a6e3a1" if running else "#f38ba8"
            status_pill = create_pill_badge(status_text, color=status_color, bg="#11111b")
            row_layout.addWidget(status_pill)

            # Restart action button
            btn_restart = QPushButton("󰑐 Restart")
            btn_restart.clicked.connect(lambda _, p=proc: self._restart_service(p))
            row_layout.addWidget(btn_restart)

            box.addWidget(row_frame)

        layout.addWidget(frame)
        layout.addStretch()
        return self._wrap_in_scroll(content)

    def _restart_service(self, proc_name: str):
        ok, msg = configuration.restart_autostart_service(proc_name)
        if ok:
            QMessageBox.information(self, "Service Restart", msg)
        else:
            QMessageBox.warning(self, "Service Error", msg)

    # --------------------------------------------------------------------------
    # Tab 6: Modular Config Files Editor
    # --------------------------------------------------------------------------
    def _editor_tab(self) -> QWidget:
        editor_widget = QWidget()
        layout = QVBoxLayout(editor_widget)
        layout.setSpacing(12)
        layout.setContentsMargins(8, 8, 8, 8)

        frame, box = card("Modular Qtile Files Editor", "Inspect and edit configuration files with automatic Python AST syntax checks.", icon="󰈔")

        selector_layout = QHBoxLayout()
        selector_layout.setSpacing(10)
        lbl = QLabel("Configuration File:")
        lbl.setStyleSheet("font-weight: 600; min-width: 140px;")
        selector_layout.addWidget(lbl)

        self.file_combo = QComboBox()
        for display_name, rel_path in configuration.CONFIG_FILES.items():
            self.file_combo.addItem(f"{display_name}  ({rel_path})", rel_path)
        self.file_combo.currentIndexChanged.connect(self._load_selected_file)
        selector_layout.addWidget(self.file_combo, 1)

        reload_file_btn = QPushButton("󰑐 Revert / Reload")
        reload_file_btn.clicked.connect(self._load_selected_file)
        selector_layout.addWidget(reload_file_btn)
        box.addLayout(selector_layout)

        self.file_editor = QPlainTextEdit()
        self.file_editor.setPlaceholderText("Loading file content...")
        box.addWidget(self.file_editor, 1)

        # Editor action toolbar
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(10)

        self.editor_status = QLabel("Ready")
        self.editor_status.setStyleSheet("color: #a6adc8; font-weight: 500;")
        actions_layout.addWidget(self.editor_status, 1)

        validate_btn = QPushButton("󰄬 Validate Syntax")
        validate_btn.clicked.connect(self._validate_editor_syntax)
        actions_layout.addWidget(validate_btn)

        save_btn = QPushButton("󰆓 Save File (Auto-backup)")
        save_btn.setObjectName("Primary")
        save_btn.clicked.connect(self._save_editor_file)
        actions_layout.addWidget(save_btn)

        box.addLayout(actions_layout)
        layout.addWidget(frame, 1)

        self._load_selected_file()
        return editor_widget

    def _load_selected_file(self):
        rel_path = self.file_combo.currentData()
        if not rel_path:
            return
        try:
            content = configuration.read_file(rel_path)
            self.file_editor.setPlainText(content)
            self.editor_status.setText(f"Loaded {rel_path}")
            self.editor_status.setStyleSheet("color: #a6e3a1; font-weight: 500;")
        except (OSError, ValueError) as exc:
            self.file_editor.setPlainText("")
            self.editor_status.setText(f"Error loading {rel_path}: {exc}")
            self.editor_status.setStyleSheet("color: #f38ba8; font-weight: 500;")

    def _validate_editor_syntax(self):
        content = self.file_editor.toPlainText()
        try:
            import ast
            ast.parse(content)
            self.editor_status.setText("✔ Python syntax valid!")
            self.editor_status.setStyleSheet("color: #a6e3a1; font-weight: 700;")
        except SyntaxError as exc:
            self.editor_status.setText(f"✘ Syntax Error: {exc}")
            self.editor_status.setStyleSheet("color: #f38ba8; font-weight: 700;")

    def _save_editor_file(self):
        rel_path = self.file_combo.currentData()
        content = self.file_editor.toPlainText()
        try:
            saved_path = configuration.save_file(rel_path, content)
            self.editor_status.setText(f"✔ Saved with backup: {saved_path.name}")
            self.editor_status.setStyleSheet("color: #a6e3a1; font-weight: 700;")

            if self.auto_reload_cb.isChecked():
                qtile.reload_qtile()
        except (OSError, ValueError, SyntaxError) as exc:
            self.editor_status.setText(f"✘ Failed to save: {exc}")
            self.editor_status.setStyleSheet("color: #f38ba8; font-weight: 700;")
            QMessageBox.critical(self, "Save Error", str(exc))
