"""Main application window for Qtile Settings & Command Center.

Hosts the branded navigation drawer, stacked central pages, and real-time filesystem
watchers for instant theme synchronization when external appearance changes occur.
"""

from __future__ import annotations

from PySide6.QtCore import QFileSystemWatcher, Qt
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from qtile_settings.adapters import themes
from qtile_settings.theme import apply_theme
from qtile_settings.ui.config_page import QtileConfigPage
from qtile_settings.ui.keybindings_page import KeybindingsPage
from qtile_settings.ui.pages import HardwarePage, NetworkPage, OverviewPage, ThemePage, ToolsPage


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("󰒋 Qtile Settings & Command Center")
        self.resize(1260, 800)
        self.setMinimumSize(960, 600)

        root = QWidget()
        layout = QHBoxLayout(root)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(14)

        # Left Sidebar / Navigation Drawer
        sidebar_col = QVBoxLayout()
        sidebar_col.setSpacing(10)

        # Branding header
        brand_frame = QFrame()
        brand_frame.setObjectName("NestedCard")
        brand_layout = QVBoxLayout(brand_frame)
        brand_layout.setContentsMargins(12, 12, 12, 12)
        brand_layout.setSpacing(2)

        self.brand_title = QLabel("󰒋 Qtile-Con")
        self.brand_title.setObjectName("BrandTitle")
        brand_layout.addWidget(self.brand_title)

        self.brand_sub = QLabel("Settings Command Center")
        self.brand_sub.setObjectName("BrandSubtitle")
        brand_layout.addWidget(self.brand_sub)
        sidebar_col.addWidget(brand_frame)

        self.sidebar = QListWidget()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(270)

        self.overview_page = OverviewPage()
        self.theme_page = ThemePage()
        self.config_page = QtileConfigPage()
        self.keys_page = KeybindingsPage()
        self.hardware_page = HardwarePage()
        self.network_page = NetworkPage()
        self.tools_page = ToolsPage()

        self.stack = QStackedWidget()
        self.pages = [
            ("󰕮  Command Center", self.overview_page),
            ("󰔎  Appearance & Theme", self.theme_page),
            ("󰒓  Qtile Configuration", self.config_page),
            ("󰌌  Keybindings & Shortcuts", self.keys_page),
            ("󰌢  Hardware & Inputs", self.hardware_page),
            ("󰖩  Network & Wi-Fi", self.network_page),
            ("󰚥  Diagnostics & System", self.tools_page),
        ]

        for name, page in self.pages:
            self.sidebar.addItem(name)
            self.stack.addWidget(page)

        self.sidebar.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.sidebar.setCurrentRow(0)

        sidebar_col.addWidget(self.sidebar, 1)

        # Sidebar footer
        status_lbl = QLabel("󰌢 Mac Ergonomics · PipeWire · X11")
        status_lbl.setObjectName("Muted")
        status_lbl.setStyleSheet("font-size: 8pt; padding: 4px;")
        status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_col.addWidget(status_lbl)

        layout.addLayout(sidebar_col)
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(root)

        # Theme synchronization
        self.theme_page.theme_changed.connect(self.reload_theme)

        # Live file system watcher for external theme modifications
        self.theme_watcher = QFileSystemWatcher(self)
        if themes.CURRENT_THEME_FILE.is_file():
            self.theme_watcher.addPath(str(themes.CURRENT_THEME_FILE))
        if themes.THEMES_DIR.is_dir():
            self.theme_watcher.addPath(str(themes.THEMES_DIR))
        self.theme_watcher.fileChanged.connect(self._on_theme_changed_external)
        self.theme_watcher.directoryChanged.connect(self._on_theme_changed_external)

    def reload_theme(self, theme_name: str | None = None) -> None:
        """Update application styling and notify open views when theme changes."""
        if not theme_name:
            theme_name = themes.get_current_theme_name()
        pal = themes.get_theme_palette(theme_name)
        app = QApplication.instance()
        if app and pal:
            apply_theme(app, pal)

        # Refresh overview badge
        self.overview_page.refresh()
        # Keep ThemePage dropdown synchronized
        self.theme_page.sync_theme(theme_name)

    def _on_theme_changed_external(self, path: str) -> None:
        """Handle theme file modifications triggered outside Qtile Settings."""
        # Re-attach watcher if the file was unlinked and recreated by an atomic save
        if themes.CURRENT_THEME_FILE.is_file() and str(themes.CURRENT_THEME_FILE) not in self.theme_watcher.files():
            self.theme_watcher.addPath(str(themes.CURRENT_THEME_FILE))
        self.reload_theme(themes.get_current_theme_name())
