"""Quick Settings floating popup view (`--quick`).

Always-on-top, compact floating control panel featuring live system load gauges,
PipeWire volume slider with mute toggle, screen brightness, keyboard backlight illumination,
instant theme selector with dynamic live updates, active network status, and shortcuts.
"""

from __future__ import annotations

from PySide6.QtCore import QFileSystemWatcher, Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from qtile_settings.adapters import audio, input_devices, network, qtile, system, themes
from qtile_settings.theme import apply_theme
from qtile_settings.ui.common import SliderSettingRow, card
from qtile_settings.ui.main_window import MainWindow


class QuickSettings(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Quick Settings")
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        self.setFixedWidth(420)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        heading = QLabel("Quick Settings")
        heading.setStyleSheet("font-size: 16pt; font-weight: 700; color: #cba6f7;")
        layout.addWidget(heading)

        # 1. System Info Gauges Card
        info = system.system_summary()
        frame, box = card("System Load", f"CPU: {info['cpu_percent']}% · RAM: {info['memory_percent']}%", icon="󰔄")
        layout.addWidget(frame)

        # 2. Audio Output Slider Card
        vol, muted, _ = audio.get_volume()
        frame, box = card("Audio Volume", icon="󰕾")
        self.volume_row = SliderSettingRow(
            "Master Volume", 0, 150, vol or 50, unit="%", icon="󰕾",
            on_change=self.change_volume
        )
        box.addWidget(self.volume_row)
        # Expose self.volume for test backwards compatibility
        self.volume = self.volume_row.slider

        mute_row = QHBoxLayout()
        self.audio_status = QLabel(f"Status: {'Muted' if muted else 'Active'}")
        self.audio_status.setStyleSheet("color: #a6adc8; font-size: 9pt;")
        mute_row.addWidget(self.audio_status)
        mute_row.addStretch()
        mute = QPushButton("Toggle Mute")
        mute.clicked.connect(self.toggle_mute)
        mute_row.addWidget(mute)
        box.addLayout(mute_row)
        layout.addWidget(frame)

        # 3. Brightness Slider Card (if supported)
        bright, _ = input_devices.get_brightness()
        if bright is not None:
            frame, box = card("Display Brightness", icon="󰛄")
            self.bright_row = SliderSettingRow(
                "Backlight", 1, 100, bright, unit="%", icon="󰃠",
                on_change=self.change_brightness
            )
            box.addWidget(self.bright_row)
            layout.addWidget(frame)

        # 4. Keyboard Backlight Card (if supported)
        kbd_bright, _ = input_devices.get_kbd_backlight()
        if kbd_bright is not None:
            frame, box = card("Keyboard Backlight", icon="󰌌")
            self.kbd_row = SliderSettingRow(
                "Illumination", 0, 100, kbd_bright, unit="%", icon="󰌌",
                on_change=input_devices.set_kbd_backlight
            )
            box.addWidget(self.kbd_row)
            layout.addWidget(frame)

        # 5. Quick Theme Switcher Card
        frame, box = card("Theme Preset", icon="󰝰")
        theme_row = QHBoxLayout()
        self.theme_picker = QComboBox()
        for name in themes.list_themes():
            self.theme_picker.addItem(name)
        curr_theme = themes.get_current_theme_name()
        t_idx = self.theme_picker.findText(curr_theme)
        if t_idx >= 0:
            self.theme_picker.setCurrentIndex(t_idx)
        self.theme_picker.currentIndexChanged.connect(self.on_theme_changed)
        theme_row.addWidget(self.theme_picker, 1)
        box.addLayout(theme_row)
        layout.addWidget(frame)

        # 5. Network Status Card
        conn = network.get_active_connection()
        net_desc = f"{conn['name']} · {conn['ip_address']}" if conn["connected"] else "Disconnected"
        frame, box = card("Network Connection", net_desc, icon="󰖩")
        self.network_desc = box.itemAt(1).widget() if box.count() > 1 else None
        refresh = QPushButton("󰑐 Refresh Network")
        refresh.clicked.connect(self.refresh_network)
        box.addWidget(refresh)
        self.network_frame = frame
        layout.addWidget(frame)

        # 6. Action Buttons
        actions_row = QHBoxLayout()
        reload_btn = QPushButton("󰑓 Reload Qtile")
        reload_btn.clicked.connect(self.quick_reload_qtile)
        open_full = QPushButton("Open Settings")
        open_full.setObjectName("Primary")
        open_full.clicked.connect(self.open_full_settings)
        actions_row.addWidget(reload_btn)
        actions_row.addWidget(open_full)
        layout.addLayout(actions_row)

        self.status = QLabel("Press 'Esc' to dismiss")
        self.status.setStyleSheet("color: #a6adc8; font-size: 8.5pt;")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        self.refreshing = False
        self.full_window = None

        # Watch for external theme changes
        self.theme_watcher = QFileSystemWatcher(self)
        if themes.CURRENT_THEME_FILE.is_file():
            self.theme_watcher.addPath(str(themes.CURRENT_THEME_FILE))
        if themes.THEMES_DIR.is_dir():
            self.theme_watcher.addPath(str(themes.THEMES_DIR))
        self.theme_watcher.fileChanged.connect(self._sync_external_theme)
        self.theme_watcher.directoryChanged.connect(self._sync_external_theme)

    def refresh_audio(self):
        volume, muted, error = audio.get_volume()
        if volume is None:
            self.audio_status.setText(f"Unavailable: {error}")
            self.volume_row.setEnabled(False)
            return
        self.audio_status.setText(f"Status: {'Muted' if muted else 'Active'} · {volume}%")
        self.refreshing = True
        self.volume_row.setValue(volume)
        self.refreshing = False
        self.volume_row.setEnabled(True)

    def change_volume(self, value: int):
        if self.refreshing:
            return
        ok, error = audio.set_volume(value)
        self.status.setText(f"Volume set to {value}%." if ok else f"Volume error: {error}")

    def toggle_mute(self):
        _, muted, error = audio.get_volume()
        if muted is None:
            self.status.setText(error)
            return
        ok, error = audio.set_muted(not muted)
        self.status.setText("Mute updated." if ok else error)
        self.refresh_audio()

    def change_brightness(self, value: int):
        input_devices.set_brightness(value)

    def on_theme_changed(self):
        theme_name = self.theme_picker.currentText()
        ok, msg = themes.apply_theme(theme_name)
        self.status.setText(msg)
        if ok:
            pal = themes.get_theme_palette(theme_name)
            app = QApplication.instance()
            if app and pal:
                apply_theme(app, pal)

    def _sync_external_theme(self, path: str):
        if themes.CURRENT_THEME_FILE.is_file() and str(themes.CURRENT_THEME_FILE) not in self.theme_watcher.files():
            self.theme_watcher.addPath(str(themes.CURRENT_THEME_FILE))
        curr = themes.get_current_theme_name()
        idx = self.theme_picker.findText(curr)
        if idx >= 0 and idx != self.theme_picker.currentIndex():
            self.theme_picker.blockSignals(True)
            self.theme_picker.setCurrentIndex(idx)
            self.theme_picker.blockSignals(False)
        pal = themes.get_theme_palette(curr)
        app = QApplication.instance()
        if app and pal:
            apply_theme(app, pal)

    def quick_reload_qtile(self):
        _, msg = qtile.reload_qtile()
        self.status.setText(f"Reload: {msg}")

    def refresh_network(self):
        conn = network.get_active_connection()
        net_desc = f"{conn['name']} · {conn['ip_address']}" if conn["connected"] else "Disconnected"
        if self.network_desc and hasattr(self.network_desc, "setText"):
            self.network_desc.setText(net_desc)

    def open_full_settings(self):
        self.full_window = MainWindow()
        self.full_window.show()
        self.full_window.raise_()
        self.full_window.activateWindow()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        super().keyPressEvent(event)
