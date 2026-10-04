"""Primary feature pages for Qtile Settings & Command Center.

Houses the primary content views:
- OverviewPage: Graphic Command Center with Fastfetch logo, session badges, and gauges
- ThemePage: Desktop theme switcher, palette color swatches, and wallpaper selector
- HardwarePage: Master audio volume, touchpad libinput gestures, and keyboard backlight
- NetworkPage: NetworkManager Wi-Fi status, AP scan list, and interface adapter table
- ToolsPage: System CLI tooling diagnostics and filesystem configuration paths
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from qtile_settings.adapters import audio, input_devices, network, qtile, system, themes, wallpaper
from qtile_settings.theme import apply_theme
from qtile_settings.ui.common import (
    SliderSettingRow,
    ToggleSettingRow,
    card,
    create_icon_badge,
    create_pill_badge,
)


class OverviewPage(QWidget):
    """Graphic Command Center dashboard with live resource gauges and Qtile session controls."""

    def __init__(self):
        super().__init__()
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        self.layout = QVBoxLayout(container)
        self.layout.setSpacing(14)
        self.layout.setContentsMargins(10, 10, 10, 10)

        # Hero Header Card with authentic Fastfetch Qtile Icon & System Metrics
        hero_frame = QFrame()
        hero_frame.setObjectName("Card")
        hero_layout = QHBoxLayout(hero_frame)
        hero_layout.setContentsMargins(16, 14, 16, 14)
        hero_layout.setSpacing(18)

        # Qtile Fastfetch ASCII/Unicode block-art logo container
        logo_container = QFrame()
        logo_container.setObjectName("NestedCard")
        logo_container.setStyleSheet(
            "background-color: #11111b; border: 1px solid #313244; border-radius: 12px; padding: 6px;"
        )
        logo_container.setFixedWidth(136)
        logo_box = QVBoxLayout(logo_container)
        logo_box.setContentsMargins(10, 8, 10, 8)
        logo_box.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.logo_label = QLabel()
        self.logo_label.setTextFormat(Qt.TextFormat.RichText)
        self.logo_label.setText(system.get_fastfetch_qtile_logo_html())
        self.logo_label.setStyleSheet("background: transparent; border: none;")
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_box.addWidget(self.logo_label)
        hero_layout.addWidget(logo_container, 0, Qt.AlignmentFlag.AlignVCenter)

        # Right information column
        info_col = QVBoxLayout()
        info_col.setSpacing(10)

        header_top = QHBoxLayout()
        header_text = QVBoxLayout()
        header_text.setSpacing(3)

        title = QLabel("Command Center")
        title.setObjectName("PageTitle")
        title.setStyleSheet("font-size: 15pt; font-weight: 700; color: #cdd6f4;")
        header_text.addWidget(title)

        subtitle = QLabel("Qtile-Con • Modern X11 Desktop & Session Orchestration")
        subtitle.setObjectName("Muted")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("font-size: 9.5pt; color: #a6adc8;")
        header_text.addWidget(subtitle)
        header_top.addLayout(header_text)

        header_top.addStretch()

        refresh_btn = QPushButton("󰑐 Refresh")
        refresh_btn.setToolTip("Refresh system metrics and environment state")
        refresh_btn.clicked.connect(self.refresh)
        header_top.addWidget(refresh_btn, 0, Qt.AlignmentFlag.AlignTop)
        info_col.addLayout(header_top)

        # Badges cluster (organized in 2 clean rows)
        badges_col = QVBoxLayout()
        badges_col.setSpacing(6)

        row1 = QHBoxLayout()
        row1.setSpacing(8)
        self.chip_host = create_pill_badge("󰌢 Host: --", color="#89b4fa", bg="#11111b")
        row1.addWidget(self.chip_host)
        self.chip_os = create_pill_badge("󰟀 OS: --", color="#cba6f7", bg="#11111b")
        row1.addWidget(self.chip_os)
        self.chip_qtile = create_pill_badge("󰒋 Qtile: --", color="#a6e3a1", bg="#11111b")
        row1.addWidget(self.chip_qtile)
        row1.addStretch()
        badges_col.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(8)
        self.chip_layout = create_pill_badge("󰕰 Layout: --", color="#94e2d5", bg="#11111b")
        row2.addWidget(self.chip_layout)
        self.chip_theme = create_pill_badge("󰔎 Theme: --", color="#f9e2af", bg="#11111b")
        row2.addWidget(self.chip_theme)
        row2.addStretch()
        badges_col.addLayout(row2)

        info_col.addLayout(badges_col)

        hero_layout.addLayout(info_col, 1)
        self.layout.addWidget(hero_frame)

        # 2. Live Resource Gauges Card
        frame, box = card("Hardware Utilization", "Real-time CPU load, memory allocation, and storage", icon="󰔄")

        # CPU Gauge
        cpu_row = QHBoxLayout()
        cpu_row.setSpacing(12)
        cpu_row.addWidget(create_icon_badge("󰻠", color="#89b4fa", size=32))
        cpu_lbl = QLabel("CPU Utilization:")
        cpu_lbl.setStyleSheet("font-weight: 600; min-width: 130px;")
        cpu_row.addWidget(cpu_lbl)
        self.cpu_bar = QProgressBar()
        self.cpu_bar.setRange(0, 100)
        self.cpu_bar.setTextVisible(False)
        cpu_row.addWidget(self.cpu_bar, 1)
        self.cpu_badge = create_pill_badge("0%", color="#89b4fa", bg="#11111b")
        cpu_row.addWidget(self.cpu_badge)
        box.addLayout(cpu_row)

        # RAM Gauge
        ram_row = QHBoxLayout()
        ram_row.setSpacing(12)
        ram_row.addWidget(create_icon_badge("󰍛", color="#a6e3a1", size=32))
        ram_lbl = QLabel("Memory Usage:")
        ram_lbl.setStyleSheet("font-weight: 600; min-width: 130px;")
        ram_row.addWidget(ram_lbl)
        self.ram_bar = QProgressBar()
        self.ram_bar.setRange(0, 100)
        self.ram_bar.setTextVisible(False)
        ram_row.addWidget(self.ram_bar, 1)
        self.ram_badge = create_pill_badge("0 GiB", color="#a6e3a1", bg="#11111b")
        ram_row.addWidget(self.ram_badge)
        box.addLayout(ram_row)

        # Storage Gauge
        disk_row = QHBoxLayout()
        disk_row.setSpacing(12)
        disk_row.addWidget(create_icon_badge("󰋊", color="#cba6f7", size=32))
        disk_lbl = QLabel("Root Storage:")
        disk_lbl.setStyleSheet("font-weight: 600; min-width: 130px;")
        disk_row.addWidget(disk_lbl)
        self.disk_bar = QProgressBar()
        self.disk_bar.setRange(0, 100)
        self.disk_bar.setTextVisible(False)
        disk_row.addWidget(self.disk_bar, 1)
        self.disk_badge = create_pill_badge("0 GiB Free", color="#cba6f7", bg="#11111b")
        disk_row.addWidget(self.disk_badge)
        box.addLayout(disk_row)
        self.layout.addWidget(frame)

        # 3. Qtile Session Controls Card
        frame, box = card("Qtile Session Operations", "Immediate IPC controls, syntax validation, and process restarts", icon="󰜉")

        actions_grid = QHBoxLayout()
        actions_grid.setSpacing(10)

        btn_check = QPushButton("󰄬 Check Config")
        btn_check.clicked.connect(self.check_config)
        actions_grid.addWidget(btn_check)

        btn_reload = QPushButton("󰑐 Reload Qtile")
        btn_reload.setObjectName("Primary")
        btn_reload.clicked.connect(self.reload_config)
        actions_grid.addWidget(btn_reload)

        btn_restart = QPushButton("󰜉 Restart Qtile")
        btn_restart.setObjectName("Danger")
        btn_restart.clicked.connect(self.restart_qtile)
        actions_grid.addWidget(btn_restart)

        btn_log = QPushButton("󰌌 Toggle Log")
        btn_log.clicked.connect(self.toggle_log)
        actions_grid.addWidget(btn_log)

        box.addLayout(actions_grid)

        self.action_status = QLabel("Ready")
        self.action_status.setStyleSheet("color: #a6adc8; font-size: 9.5pt;")
        box.addWidget(self.action_status)

        # Expandable Runtime Log Container
        self.log_frame = QFrame()
        self.log_frame.setObjectName("NestedCard")
        log_box = QVBoxLayout(self.log_frame)
        log_box.setContentsMargins(10, 10, 10, 10)

        log_head = QHBoxLayout()
        log_head.addWidget(QLabel("<b>Qtile Runtime Log (~/.local/share/qtile/qtile.log)</b>"))
        log_head.addStretch()
        refresh_log_btn = QPushButton("󰑐 Refresh Log")
        refresh_log_btn.clicked.connect(self._refresh_log_content)
        log_head.addWidget(refresh_log_btn)
        log_box.addLayout(log_head)

        self.log_viewer = QPlainTextEdit()
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setMaximumHeight(180)
        self.log_viewer.setStyleSheet("background: #11111b; color: #cdd6f4; font-family: JetBrains Mono, monospace; font-size: 8.5pt; border: none;")
        log_box.addWidget(self.log_viewer)

        self.log_frame.setVisible(False)
        box.addWidget(self.log_frame)
        self.layout.addWidget(frame)

        self.layout.addStretch()

        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        self.refresh()

    def refresh(self):
        info = system.system_summary()
        qver = qtile.get_qtile_version()
        current_theme = themes.get_current_theme_name()
        current_layout = qtile.get_current_layout()

        self.logo_label.setText(system.get_fastfetch_qtile_logo_html())
        self.chip_host.setText(f"󰌢 {info['hostname']}")
        self.chip_os.setText(f"󰟀 {info['os']}")
        self.chip_qtile.setText(f"󰒋 Qtile {qver}")
        self.chip_layout.setText(f"󰕰 {current_layout}")
        self.chip_theme.setText(f"󰔎 {current_theme}")

        cpu_val = int(info["cpu_percent"])
        self.cpu_bar.setValue(cpu_val)
        self.cpu_badge.setText(f"{cpu_val}%")

        ram_used = info["memory_used_gib"]
        ram_total = info["memory_total_gib"]
        ram_pct = int(info["memory_percent"])
        self.ram_bar.setValue(ram_pct)
        self.ram_badge.setText(f"{ram_used} / {ram_total} GiB ({ram_pct}%)")

        disk_pct = int(info["disk_percent"])
        disk_free = info["disk_free_gib"]
        self.disk_bar.setValue(disk_pct)
        self.disk_badge.setText(f"{disk_free} GiB Free ({disk_pct}%)")

    refresh_overview = refresh

    def check_config(self):
        ok, msg = qtile.check_config()
        self.action_status.setText(f"Check result: {msg}")
        if not ok:
            QMessageBox.warning(self, "Qtile Config Check", msg)

    def reload_config(self):
        _, msg = qtile.reload_qtile()
        self.action_status.setText(f"Reload: {msg}")

    def restart_qtile(self):
        reply = QMessageBox.question(
            self,
            "Restart Qtile",
            "Are you sure you want to restart Qtile? Running client windows will be preserved, but the window manager will reinitialize.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            _, msg = qtile.restart_qtile()
            self.action_status.setText(f"Restart: {msg}")

    def toggle_log(self):
        show = self.log_frame.isHidden()
        if show:
            self._refresh_log_content()
        self.log_frame.setVisible(show)

    def _refresh_log_content(self):
        self.log_viewer.setPlainText(qtile.get_qtile_log(60))


class ThemePage(QWidget):
    """Appearance settings: Qtile themes and desktop wallpaper."""

    theme_changed = Signal(str)

    def __init__(self):
        super().__init__()
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(14)
        layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel("Appearance & Themes")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        desc = QLabel("Preset palettes synchronized across Qtile bar, terminal emulators, editors, and launchers.")
        desc.setObjectName("Muted")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # 1. Preset Themes Card
        frame, box = card("Qtile-Con Color Themes", "Select and apply a color preset across the desktop environment", icon="󰔎")

        picker_row = QHBoxLayout()
        lbl = QLabel("Active Preset:")
        lbl.setStyleSheet("font-weight: 600; min-width: 120px;")
        picker_row.addWidget(lbl)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(themes.list_themes())
        current = themes.get_current_theme_name()
        idx = self.theme_combo.findText(current)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)
        self.theme_combo.currentIndexChanged.connect(self.on_theme_selected)
        picker_row.addWidget(self.theme_combo, 1)

        self.apply_btn = QPushButton("󰄬 Apply Theme")
        self.apply_btn.setObjectName("Primary")
        self.apply_btn.clicked.connect(self.apply_theme)
        picker_row.addWidget(self.apply_btn)
        box.addLayout(picker_row)

        self.palette_preview = QLabel()
        self.palette_preview.setTextFormat(Qt.TextFormat.RichText)
        self.palette_preview.setObjectName("NestedCard")
        self.palette_preview.setStyleSheet("border-radius: 8px; padding: 10px;")
        box.addWidget(self.palette_preview)

        self.status = QLabel("Theme ready.")
        self.status.setObjectName("Muted")
        box.addWidget(self.status)
        layout.addWidget(frame)

        # 2. Desktop Wallpaper Card
        frame, box = card("Desktop Wallpaper", "Select and set your background image via feh", icon="󰸉")
        wall_row = QHBoxLayout()
        w_lbl = QLabel("Wallpaper:")
        w_lbl.setStyleSheet("font-weight: 600; min-width: 120px;")
        wall_row.addWidget(w_lbl)

        self.wall_combo = QComboBox()
        self.walls = wallpaper.list_wallpapers()
        if self.walls:
            self.wall_combo.addItems([w.name for w in self.walls])
        else:
            self.wall_combo.addItem("No wallpapers found in directory")
        wall_row.addWidget(self.wall_combo, 1)

        self.set_wall_btn = QPushButton("󰸉 Set Wallpaper")
        self.set_wall_btn.clicked.connect(self.apply_wallpaper)
        wall_row.addWidget(self.set_wall_btn)
        box.addLayout(wall_row)

        wall_dir_display = str(wallpaper.get_wallpaper_dir()).replace(str(Path.home()), "~")
        self.wall_status = QLabel(f"Wallpaper directory: {wall_dir_display}")
        self.wall_status.setObjectName("Muted")
        box.addWidget(self.wall_status)
        layout.addWidget(frame)

        layout.addStretch()

        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        self.preview_theme()

    def preview_theme(self):
        name = self.theme_combo.currentText()
        pal = themes.get_theme_palette(name)
        if not pal:
            self.palette_preview.setText("<i>Palette data preview unavailable</i>")
            return

        swatches = []
        for color_key in ["base", "surface0", "blue", "lavender", "green", "mauve", "yellow", "red"]:
            hex_val = pal.get(color_key, "#45475a")
            swatches.append(f"<span style='color:{hex_val}; font-size: 13pt;'>■ {color_key}</span>: <code>{hex_val}</code>")
        self.palette_preview.setText("&nbsp;&nbsp;&nbsp;&nbsp;".join(swatches))

    def on_theme_selected(self, index: int):
        name = self.theme_combo.currentText()
        if not name:
            return
        self.preview_theme()
        ok, msg = themes.apply_theme(name)
        self.status.setText(msg)
        if ok:
            pal = themes.get_theme_palette(name)
            app = QApplication.instance()
            if app and pal:
                apply_theme(app, pal)
            qtile.reload_qtile()
            self.theme_changed.emit(name)

    def sync_theme(self, theme_name: str):
        idx = self.theme_combo.findText(theme_name)
        if idx >= 0 and idx != self.theme_combo.currentIndex():
            self.theme_combo.blockSignals(True)
            self.theme_combo.setCurrentIndex(idx)
            self.theme_combo.blockSignals(False)
            self.preview_theme()

    def apply_theme(self):
        name = self.theme_combo.currentText()
        ok, msg = themes.apply_theme(name)
        self.status.setText(msg)
        if ok:
            pal = themes.get_theme_palette(name)
            app = QApplication.instance()
            if app and pal:
                apply_theme(app, pal)
            qtile.reload_qtile()
            self.theme_changed.emit(name)

    def apply_wallpaper(self):
        idx = self.wall_combo.currentIndex()
        if 0 <= idx < len(self.walls):
            wall_path = str(self.walls[idx])
            ok, msg = wallpaper.set_wallpaper(wall_path)
            msg_sanitized = msg.replace(str(Path.home()), "~")
            self.wall_status.setText(msg_sanitized if ok else f"Failed: {msg_sanitized}")


class HardwarePage(QWidget):
    """Audio, touchpad gestures, and display controls."""

    def __init__(self):
        super().__init__()
        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(14)
        layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel("Hardware & Inputs")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        desc = QLabel("Configure master audio sink, touchpad gestures, and X11 display information.")
        desc.setObjectName("Muted")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Audio Output Card
        frame, box = card("Master Audio Output (PipeWire / WirePlumber)", icon="󰕾")
        vol, muted, _ = audio.get_volume()
        self.audio_slider = SliderSettingRow(
            "Master Volume", 0, 150, vol or 50, unit="%", icon="󰕾",
            description="System output volume level (can boost above 100%)",
            on_change=self.change_volume
        )
        self.volume_slider = self.audio_slider.slider
        box.addWidget(self.audio_slider)

        mute_row = QHBoxLayout()
        self.audio_status = QLabel(f"Status: {'Muted' if muted else 'Active'}")
        self.audio_status.setStyleSheet("color: #a6adc8; font-weight: 500;")
        mute_row.addWidget(self.audio_status)
        mute_row.addStretch()
        self.mute_btn = QPushButton("Toggle Mute")
        self.mute_btn.clicked.connect(self.toggle_mute)
        mute_row.addWidget(self.mute_btn)
        box.addLayout(mute_row)
        layout.addWidget(frame)

        # Touchpad Card
        frame, box = card("Touchpad & Gestures", "Libinput tapping and natural scrolling settings", icon="󰌢")
        tp_status = input_devices.get_touchpad_status()
        if tp_status.available:
            dev_lbl = QLabel(f"Detected Hardware: <b>{tp_status.device_name}</b> (ID: {tp_status.device_id})")
            dev_lbl.setStyleSheet("color: #89b4fa; font-weight: 500;")
            box.addWidget(dev_lbl)

            self.tap_toggle = ToggleSettingRow(
                "Enable Tap-to-Click",
                "Single-tap for left click, two-finger tap for right click, three-finger for middle click",
                checked=tp_status.tapping_enabled,
                icon="󰌢",
                on_toggle=self.on_tapping_toggled,
            )
            box.addWidget(self.tap_toggle)

            self.scroll_toggle = ToggleSettingRow(
                "Natural Scrolling",
                "Reverse scroll direction so content tracks finger movement naturally",
                checked=tp_status.natural_scrolling,
                icon="󰆾",
                on_toggle=self.on_natural_scrolling_toggled,
            )
            box.addWidget(self.scroll_toggle)

            self.tp_status_label = QLabel("Touchpad configuration active.")
            self.tp_status_label.setStyleSheet("color: #a6adc8; font-size: 9pt;")
            box.addWidget(self.tp_status_label)
        else:
            box.addWidget(QLabel("No configurable libinput touchpad was detected on this session."))
        layout.addWidget(frame)

        # Keyboard Backlight Card
        frame, box = card("Keyboard Backlight & Illumination", "Hardware keyboard backlighting and key brightness levels", icon="󰌌")
        kbd_bright, kbd_dev = input_devices.get_kbd_backlight()
        if kbd_bright is not None:
            dev_str = f"<b>{kbd_dev}</b>" if kbd_dev else "Hardware controller"
            dev_lbl = QLabel(f"Detected Controller: {dev_str}")
            dev_lbl.setStyleSheet("color: #89b4fa; font-weight: 500;")
            box.addWidget(dev_lbl)

            self.kbd_slider = SliderSettingRow(
                "Keyboard Brightness", 0, 100, kbd_bright, unit="%", icon="󰌌",
                description="Illumination intensity level for keyboard keys",
                on_change=self.change_kbd_backlight,
            )
            box.addWidget(self.kbd_slider)

            btn_row = QHBoxLayout()
            self.kbd_status_label = QLabel(f"Active illumination: {kbd_bright}%")
            self.kbd_status_label.setStyleSheet("color: #a6adc8; font-size: 9pt;")
            btn_row.addWidget(self.kbd_status_label)
            btn_row.addStretch()

            btn_off = QPushButton("󰌐 Off")
            btn_off.setToolTip("Turn off keyboard backlight completely")
            btn_off.clicked.connect(lambda: self.set_kbd_backlight_preset(0))
            btn_row.addWidget(btn_off)

            btn_25 = QPushButton("25%")
            btn_25.clicked.connect(lambda: self.set_kbd_backlight_preset(25))
            btn_row.addWidget(btn_25)

            btn_50 = QPushButton("50%")
            btn_50.clicked.connect(lambda: self.set_kbd_backlight_preset(50))
            btn_row.addWidget(btn_50)

            btn_75 = QPushButton("75%")
            btn_75.clicked.connect(lambda: self.set_kbd_backlight_preset(75))
            btn_row.addWidget(btn_75)

            btn_full = QPushButton("100%")
            btn_full.clicked.connect(lambda: self.set_kbd_backlight_preset(100))
            btn_row.addWidget(btn_full)

            box.addLayout(btn_row)
        else:
            no_kbd = QLabel("No controllable keyboard backlight device (e.g. smc::kbd_backlight) was detected.")
            no_kbd.setObjectName("Muted")
            box.addWidget(no_kbd)
        layout.addWidget(frame)

        # Display & Brightness Card
        frame, box = card("Display & Backlight", "X11 outputs, active resolutions, and screen brightness", icon="󰛄")
        bright, _ = input_devices.get_brightness()
        if bright is not None:
            self.bright_slider = SliderSettingRow(
                "Screen Brightness", 1, 100, bright, unit="%", icon="󰃠",
                description="Display backlight intensity",
                on_change=self.change_brightness
            )
            box.addWidget(self.bright_slider)

        self.display_label = QLabel(system.display_summary())
        self.display_label.setWordWrap(True)
        self.display_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.display_label.setStyleSheet(
            "background: #11111b; border: 1px solid #363a4f; border-radius: 8px; padding: 10px; "
            "font-family: 'JetBrainsMono Nerd Font', 'JetBrains Mono', monospace; font-size: 8.5pt; color: #cdd6f4;"
        )
        box.addWidget(self.display_label)
        layout.addWidget(frame)

        layout.addStretch()

        self.scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self.scroll)

        self.refreshing_audio = False

    def change_volume(self, val: int):
        if self.refreshing_audio:
            return
        ok, err = audio.set_volume(val)
        if ok:
            self.audio_status.setText("Status: Active")
        else:
            self.audio_status.setText(f"Volume error: {err}")

    def toggle_mute(self):
        _, muted, err = audio.get_volume()
        if muted is None:
            self.audio_status.setText(f"Audio unavailable: {err}")
            return
        ok, err = audio.set_muted(not muted)
        if ok:
            new_muted = not muted
            self.audio_status.setText(f"Status: {'Muted' if new_muted else 'Active'}")
        else:
            self.audio_status.setText(f"Mute error: {err}")

    def on_tapping_toggled(self, checked: bool):
        ok, msg = input_devices.set_touchpad_property("tapping", checked)
        self.tp_status_label.setText(msg if ok else f"Failed: {msg}")

    def on_natural_scrolling_toggled(self, checked: bool):
        ok, msg = input_devices.set_touchpad_property("natural_scrolling", checked)
        self.tp_status_label.setText(msg if ok else f"Failed: {msg}")

    def change_brightness(self, val: int):
        input_devices.set_brightness(val)

    def change_kbd_backlight(self, val: int):
        ok, msg = input_devices.set_kbd_backlight(val)
        if hasattr(self, "kbd_status_label"):
            if ok:
                self.kbd_status_label.setText(f"Active illumination: {val}%")
            else:
                self.kbd_status_label.setText(f"Error: {msg}")

    def set_kbd_backlight_preset(self, val: int):
        if hasattr(self, "kbd_slider"):
            self.kbd_slider.slider.setValue(val)


def _signal_icon(pct: int) -> str:
    """Return an appropriate Material Wi-Fi symbol based on signal strength."""
    if pct >= 75:
        return "󰤨"
    if pct >= 50:
        return "󰤥"
    if pct >= 25:
        return "󰤢"
    return "󰤟"


class NetworkPage(QWidget):
    """Comprehensive graphical Network & Connectivity page."""

    def __init__(self):
        super().__init__()
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(14)
        layout.setContentsMargins(10, 10, 10, 10)

        # Header Title
        title_box = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title = QLabel("Network & Connectivity")
        title.setObjectName("PageTitle")
        title_col.addWidget(title)
        desc = QLabel("Active network connection details, Wi-Fi radio status, and nearby wireless access points.")
        desc.setObjectName("Muted")
        title_col.addWidget(desc)
        title_box.addLayout(title_col, 1)

        self.btn_rescan = QPushButton("󱚽 Rescan Wi-Fi")
        self.btn_rescan.clicked.connect(self.rescan_wifi)
        title_box.addWidget(self.btn_rescan)

        self.btn_refresh = QPushButton("󰑐 Refresh")
        self.btn_refresh.clicked.connect(self.refresh)
        title_box.addWidget(self.btn_refresh)

        layout.addLayout(title_box)

        # 1. Primary Active Connection Card
        frame, self.active_box = card("Active Network Connection", "Primary default route and IP addressing", icon="󰖩")

        self.active_status_widget = QWidget()
        self.active_status_layout = QVBoxLayout(self.active_status_widget)
        self.active_status_layout.setContentsMargins(0, 0, 0, 0)
        self.active_box.addWidget(self.active_status_widget)
        layout.addWidget(frame)

        # 2. Wi-Fi Radio Switch Card
        frame, wifi_box = card("Wi-Fi Radio & Control", "Hardware radio state and wireless adapter", icon="󰖩")
        self.wifi_radio_toggle = ToggleSettingRow(
            "Enable Wi-Fi Radio",
            "Turn wireless interface on or off via NetworkManager",
            checked=network.get_wifi_radio_enabled(),
            icon="󰖩",
            on_toggle=self.toggle_wifi_radio,
        )
        wifi_box.addWidget(self.wifi_radio_toggle)
        layout.addWidget(frame)

        # 3. Available Wi-Fi Networks Card
        frame, self.wifi_list_box = card("Nearby Wireless Networks", "Scanned Wi-Fi access points", icon="󰤨")
        self.wifi_table = QTableWidget()
        self.wifi_table.setColumnCount(5)
        self.wifi_table.setHorizontalHeaderLabels(["Network (SSID)", "Signal", "Band", "Security", "Action"])
        self.wifi_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.wifi_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.wifi_table.setColumnWidth(1, 100)
        self.wifi_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.wifi_table.setColumnWidth(2, 95)
        self.wifi_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.wifi_table.setColumnWidth(3, 115)
        self.wifi_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.wifi_table.setColumnWidth(4, 105)
        self.wifi_table.verticalHeader().setVisible(False)
        self.wifi_table.verticalHeader().setDefaultSectionSize(38)
        self.wifi_table.setAlternatingRowColors(True)
        self.wifi_table.setShowGrid(True)
        self.wifi_table.setMinimumHeight(160)
        self.wifi_table.setMaximumHeight(260)
        self.wifi_list_box.addWidget(self.wifi_table)
        layout.addWidget(frame)

        # 4. Detected Interfaces Card
        frame, self.iface_box = card("Detected Network Interfaces", "Physical and virtual network adapters", icon="󰒓")
        self.iface_table = QTableWidget()
        self.iface_table.setColumnCount(4)
        self.iface_table.setHorizontalHeaderLabels(["Device", "Type", "State", "Active Connection"])
        self.iface_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.iface_table.setColumnWidth(0, 130)
        self.iface_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.iface_table.setColumnWidth(1, 115)
        self.iface_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.iface_table.setColumnWidth(2, 165)
        self.iface_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.iface_table.verticalHeader().setVisible(False)
        self.iface_table.verticalHeader().setDefaultSectionSize(36)
        self.iface_table.setAlternatingRowColors(True)
        self.iface_table.setShowGrid(True)
        self.iface_table.setMinimumHeight(140)
        self.iface_table.setMaximumHeight(220)
        self.iface_box.addWidget(self.iface_table)
        layout.addWidget(frame)

        layout.addStretch()

        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        self.refresh()

    def refresh(self):
        # Clear active status widget
        while self.active_status_layout.count():
            item = self.active_status_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    sub = item.layout().takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()

        info = network.get_active_connection()

        if info["connected"]:
            conn_header = QHBoxLayout()
            icon_str = "󰖩" if info["type"] == "wifi" else "󰌗"
            conn_header.addWidget(create_icon_badge(icon_str, color="#89b4fa", size=42))

            name_col = QVBoxLayout()
            name_col.setSpacing(2)
            name_lbl = QLabel(f"<b>{info['name']}</b> ({info['device']})")
            name_lbl.setStyleSheet("font-size: 12pt; color: #cdd6f4;")
            name_col.addWidget(name_lbl)
            type_lbl = QLabel(f"Type: {info['type'].upper()}  ·  Hardware MAC: {info.get('hw_addr', '--')}")
            type_lbl.setObjectName("Muted")
            name_col.addWidget(type_lbl)
            conn_header.addLayout(name_col, 1)

            pill = create_pill_badge("● Connected", color="#a6e3a1", bg="#11111b")
            conn_header.addWidget(pill)
            self.active_status_layout.addLayout(conn_header)

            # Details Grid
            details_frame = QFrame()
            details_frame.setObjectName("NestedCard")
            details_layout = QVBoxLayout(details_frame)
            details_layout.setSpacing(8)

            row1 = QHBoxLayout()
            row1.addWidget(QLabel(f"<b>IPv4 Address:</b> <code>{info['ip_address'] or 'N/A'}</code>"))
            row1.addStretch()
            row1.addWidget(QLabel(f"<b>Gateway:</b> <code>{info['gateway'] or 'N/A'}</code>"))
            row1.addStretch()
            dns_str = ", ".join(info['dns']) if info['dns'] else "N/A"
            row1.addWidget(QLabel(f"<b>DNS:</b> <code>{dns_str}</code>"))
            details_layout.addLayout(row1)

            if info["type"] == "wifi":
                row2 = QHBoxLayout()
                sig_pct = info.get("signal_percent", 0)
                bars = info.get("signal_bars", "")
                sig_icon = _signal_icon(sig_pct)
                row2.addWidget(QLabel(f"<b>Signal Quality:</b> {sig_icon} {bars} {sig_pct}%"))
                row2.addStretch()
                row2.addWidget(QLabel(f"<b>Frequency:</b> {info.get('frequency', '--')}"))
                row2.addStretch()
                row2.addWidget(QLabel(f"<b>Security:</b> {info.get('security', '--')}"))
                details_layout.addLayout(row2)

            self.active_status_layout.addWidget(details_frame)
        else:
            offline_lbl = QLabel("<span style='font-size: 14pt; color: #f38ba8;'>󰅛</span> <b>No active network connection detected.</b>")
            offline_lbl.setStyleSheet("padding: 10px;")
            self.active_status_layout.addWidget(offline_lbl)

        # Refresh Wi-Fi Table
        aps = network.scan_wifi_networks()
        self.wifi_table.setRowCount(len(aps))
        for row_idx, ap in enumerate(aps):
            ssid_text = ap["ssid"]
            if ap["in_use"]:
                ssid_item = QTableWidgetItem(f"󰖩  {ssid_text}")
                ssid_item.setForeground(QColor("#a6e3a1"))
                f = ssid_item.font()
                f.setBold(True)
                ssid_item.setFont(f)
            else:
                ssid_item = QTableWidgetItem(f"   {ssid_text}")
                ssid_item.setForeground(QColor("#cdd6f4"))
            ssid_item.setFlags(ssid_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.wifi_table.setItem(row_idx, 0, ssid_item)

            sig_pct = ap.get("signal", 0)
            sig_icon = _signal_icon(sig_pct)
            sig_item = QTableWidgetItem(f"{sig_icon}  {sig_pct}%")
            sig_item.setForeground(QColor("#89b4fa"))
            sig_item.setFlags(sig_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.wifi_table.setItem(row_idx, 1, sig_item)

            band_label = ap.get("band_label") or "2.4 GHz"
            band_item = QTableWidgetItem(band_label)
            band_item.setForeground(QColor("#b4befe"))
            band_item.setFlags(band_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.wifi_table.setItem(row_idx, 2, band_item)

            sec_item = QTableWidgetItem(ap.get("security", "Open"))
            sec_item.setForeground(QColor("#a6adc8"))
            sec_item.setFlags(sec_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.wifi_table.setItem(row_idx, 3, sec_item)

            if ap["in_use"]:
                pill = create_pill_badge("Active", color="#a6e3a1", bg="#181825")
                self.wifi_table.setCellWidget(row_idx, 4, pill)
            else:
                btn_conn = QPushButton("Connect")
                btn_conn.setStyleSheet("padding: 3px 10px; font-size: 8.5pt;")
                btn_conn.clicked.connect(lambda _, s=ap["ssid"]: self.connect_wifi(s))
                self.wifi_table.setCellWidget(row_idx, 4, btn_conn)

        # Refresh Interfaces Table
        ifaces = network.list_all_interfaces()
        self.iface_table.setRowCount(len(ifaces))
        for row_idx, iface in enumerate(ifaces):
            dev_item = QTableWidgetItem(iface["device"])
            dev_item.setForeground(QColor("#89b4fa"))
            dev_item.setFlags(dev_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.iface_table.setItem(row_idx, 0, dev_item)

            type_item = QTableWidgetItem(iface["type"])
            type_item.setForeground(QColor("#cdd6f4"))
            type_item.setFlags(type_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.iface_table.setItem(row_idx, 1, type_item)

            state_item = QTableWidgetItem(iface["state"])
            state_item.setFlags(state_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if "connected" in iface["state"].lower():
                state_item.setForeground(QColor("#a6e3a1"))
            else:
                state_item.setForeground(QColor("#a6adc8"))
            self.iface_table.setItem(row_idx, 2, state_item)

            conn_item = QTableWidgetItem(iface["connection"])
            conn_item.setForeground(QColor("#cdd6f4"))
            conn_item.setFlags(conn_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.iface_table.setItem(row_idx, 3, conn_item)

    def toggle_wifi_radio(self, checked: bool):
        ok, msg = network.set_wifi_radio(checked)
        if not ok:
            QMessageBox.warning(self, "Wi-Fi Radio", msg)
        self.refresh()

    def rescan_wifi(self):
        ok, msg = network.rescan_wifi()
        if not ok:
            QMessageBox.warning(self, "Wi-Fi Rescan", msg)
        self.refresh()

    def connect_wifi(self, ssid: str):
        ok, msg = network.connect_wifi(ssid)
        if ok:
            QMessageBox.information(self, "Wi-Fi Connection", f"Connected to {ssid} successfully.")
        else:
            QMessageBox.warning(self, "Connection Error", msg)
        self.refresh()


class ToolsPage(QWidget):
    """System tools availability and integration diagnostic status."""

    def __init__(self):
        super().__init__()
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        self.layout = QVBoxLayout(container)
        self.layout.setSpacing(14)
        self.layout.setContentsMargins(12, 12, 12, 12)

        header_top = QHBoxLayout()
        header_text = QVBoxLayout()
        header_text.setSpacing(3)

        title = QLabel("System Integration & Diagnostics")
        title.setObjectName("PageTitle")
        title.setWordWrap(True)
        header_text.addWidget(title)

        desc = QLabel("Verification of external commands, system daemons, and filesystem configuration paths.")
        desc.setObjectName("Muted")
        desc.setWordWrap(True)
        header_text.addWidget(desc)
        header_top.addLayout(header_text, 1)

        refresh_btn = QPushButton("󰑐 Run Diagnostic Check")
        refresh_btn.setToolTip("Re-scan system tools, backends, and filesystem paths")
        refresh_btn.clicked.connect(self.refresh)
        header_top.addWidget(refresh_btn, 0, Qt.AlignmentFlag.AlignTop)
        self.layout.addLayout(header_top)

        self.cards_layout = QVBoxLayout()
        self.cards_layout.setSpacing(14)
        self.layout.addLayout(self.cards_layout)

        self.layout.addStretch()

        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        self.refresh()

    def refresh(self):
        # Clear previous cards
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    sub = item.layout().takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()

        # 1. Detected System CLI Utilities Card
        frame, box = card("Detected System CLI Utilities", "Hardware controllers, display query tools, and network backends", icon="󰒓")
        kbd_present = input_devices.has_kbd_backlight()
        kbd_dev = input_devices.find_kbd_backlight_device() or "None"
        tools = [
            ("nmcli", shutil.which("nmcli") is not None, "󰖩", "NetworkManager connection and Wi-Fi adapter manager"),
            ("wpctl", system.available_tools().get("wpctl", False), "󰕾", "PipeWire / WirePlumber audio and media volume backend"),
            ("xrandr", system.available_tools().get("xrandr", False), "󰍹", "X11 resolution and multi-monitor output detection"),
            ("bluetoothctl", system.available_tools().get("bluetoothctl", False), "󰂯", "BlueZ Bluetooth daemon and device pairing manager"),
            ("brightnessctl", shutil.which("brightnessctl") is not None, "󰃠", "Display and keyboard backlight intensity controller"),
            ("kbd_backlight", kbd_present, "󰌌", f"Keyboard backlight hardware driver ({kbd_dev})"),
            ("xinput", shutil.which("xinput") is not None, "󰌢", "Libinput touchpad tapping and natural scrolling driver"),
            ("feh", os.path.exists("/usr/bin/feh") or shutil.which("feh") is not None, "󰸉", "X11 root window wallpaper setting utility"),
        ]

        for name, present, icon, desc_text in tools:
            row_frame = QFrame()
            row_frame.setObjectName("SettingRow")
            row_frame.setMinimumHeight(48)
            row_lay = QHBoxLayout(row_frame)
            row_lay.setContentsMargins(8, 6, 8, 6)
            row_lay.setSpacing(12)

            badge = create_icon_badge(icon, color="#89b4fa" if present else "#a6adc8", size=34)
            row_lay.addWidget(badge)

            text_col = QVBoxLayout()
            text_col.setSpacing(2)
            title_lbl = QLabel(f"<b>{name}</b>")
            title_lbl.setStyleSheet("color: #cdd6f4; font-size: 10pt; font-weight: 600;")
            text_col.addWidget(title_lbl)
            d_lbl = QLabel(desc_text)
            d_lbl.setObjectName("Muted")
            d_lbl.setWordWrap(True)
            d_lbl.setStyleSheet("color: #a6adc8; font-size: 8.8pt;")
            text_col.addWidget(d_lbl)
            row_lay.addLayout(text_col, 1)

            status_pill = create_pill_badge("● Ready" if present else "● Missing", color="#a6e3a1" if present else "#f38ba8", bg="#11111b")
            row_lay.addWidget(status_pill)
            box.addWidget(row_frame)
        self.cards_layout.addWidget(frame)

        # 2. Configuration & Log Paths Card
        frame, box = card("Configuration & Log Paths", "Filesystem targets and environment paths managed by Qtile Settings", icon="󰋊")
        paths = [
            ("Active Qtile Config", str(qtile.config_path()), "󰒓", qtile.config_path().is_file()),
            ("Theme Presets", str(themes.THEMES_DIR), "󰔎", themes.THEMES_DIR.is_dir()),
            ("Wallpaper Directory", str(wallpaper.get_wallpaper_dir()), "󰸉", wallpaper.get_wallpaper_dir().is_dir()),
            ("Runtime Log", str(qtile.LOG_FILE), "󰌌", qtile.LOG_FILE.is_file()),
        ]
        for title_str, path_str, icon, exists in paths:
            row_frame = QFrame()
            row_frame.setObjectName("SettingRow")
            row_frame.setMinimumHeight(48)
            row_lay = QHBoxLayout(row_frame)
            row_lay.setContentsMargins(8, 6, 8, 6)
            row_lay.setSpacing(12)

            badge = create_icon_badge(icon, color="#cba6f7", size=34)
            row_lay.addWidget(badge)

            text_col = QVBoxLayout()
            text_col.setSpacing(2)
            t_lbl = QLabel(f"<b>{title_str}</b>")
            t_lbl.setStyleSheet("color: #cdd6f4; font-size: 10pt; font-weight: 600;")
            text_col.addWidget(t_lbl)
            p_lbl = QLabel(f"<code>{path_str}</code>")
            p_lbl.setStyleSheet("color: #89b4fa; font-family: 'JetBrainsMono Nerd Font', 'JetBrains Mono', monospace; font-size: 8.8pt;")
            p_lbl.setWordWrap(True)
            text_col.addWidget(p_lbl)
            row_lay.addLayout(text_col, 1)

            pill = create_pill_badge("● Present" if exists else "● Missing", color="#a6e3a1" if exists else "#f38ba8", bg="#11111b")
            row_lay.addWidget(pill)
            box.addWidget(row_frame)
        self.cards_layout.addWidget(frame)
