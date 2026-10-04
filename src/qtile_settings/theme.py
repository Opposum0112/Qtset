"""Theming and Material 3 styling subsystem.

Provides dynamic token mapping from Qtile color palettes (Catppuccin Mocha/Frappe/Latte,
Gruvbox, Ayu, Solarized, GitHub Dark) to Material 3 semantic roles (surface, outline,
containers, accents). Injects the global Qt stylesheet and QPalette into QApplication.
"""

from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication

# Default Material 3 & Catppuccin Mocha palette aligned with DankMaterialShell
COLORS = {
    "surface": "#181825",
    "surfaceContainer": "#1e1e2e",
    "surfaceContainerHigh": "#252538",
    "surfaceContainerHighest": "#313244",
    "outline": "#363a4f",
    "outlineVariant": "#282a36",
    "base": "#1e1e2e",
    "mantle": "#181825",
    "crust": "#11111b",
    "surface0": "#313244",
    "surface1": "#45475a",
    "surface2": "#585b70",
    "text": "#cdd6f4",
    "subtext": "#a6adc8",
    "muted": "#6c7086",
    "blue": "#89b4fa",
    "lavender": "#b4befe",
    "green": "#a6e3a1",
    "yellow": "#f9e2af",
    "red": "#f38ba8",
    "mauve": "#cba6f7",
    "peach": "#fab387",
    "teal": "#94e2d5",
}


def resolve_theme_colors(palette: dict[str, str] | None = None) -> dict[str, str]:
    """Map theme palette (Catppuccin, Gruvbox, Ayu, Solarized, Latte, etc.) to full Material 3 token set."""
    colors = dict(COLORS)
    if not palette:
        return colors

    # Extract base tokens from theme dictionary
    mantle = palette.get("mantle", palette.get("surface", COLORS["surface"]))
    base = palette.get("base", palette.get("surfaceContainer", COLORS["surfaceContainer"]))
    crust = palette.get("crust", COLORS["crust"])
    surface0 = palette.get("surface0", COLORS["surface0"])
    surface1 = palette.get("surface1", COLORS["surface1"])
    surface2 = palette.get("surface2", COLORS["surface2"])
    overlay = palette.get("overlay", COLORS["muted"])

    derived = {
        "surface": mantle,
        "surfaceContainer": base,
        "surfaceContainerHigh": surface0,
        "surfaceContainerHighest": surface1,
        "outline": surface2,
        "outlineVariant": surface1,
        "muted": overlay,
        "crust": crust,
        "base": base,
        "mantle": mantle,
        "surface0": surface0,
        "surface1": surface1,
        "surface2": surface2,
    }
    colors.update(derived)
    colors.update(palette)
    return colors


def apply_theme(app: QApplication, palette: dict[str, str] | None = None) -> None:
    """Apply the resolved Material 3 color palette and Qt stylesheet to QApplication.

    Args:
        app: Active QApplication instance to style.
        palette: Optional dictionary of hex color overrides from theme JSON.
    """
    colors = resolve_theme_colors(palette)

    app.setStyle("Fusion")

    # Set application font with Nerd Font support
    app_font = QFont("JetBrainsMono Nerd Font Propo", 10)
    app_font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(app_font)

    # Dynamic system palette ensuring un-styled sub-widgets match active theme
    theme_palette = QPalette()
    theme_palette.setColor(QPalette.ColorRole.Window, QColor(colors["surface"]))
    theme_palette.setColor(QPalette.ColorRole.WindowText, QColor(colors["text"]))
    theme_palette.setColor(QPalette.ColorRole.Base, QColor(colors["crust"]))
    theme_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(colors["surfaceContainerHigh"]))
    theme_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(colors["crust"]))
    theme_palette.setColor(QPalette.ColorRole.ToolTipText, QColor(colors["text"]))
    theme_palette.setColor(QPalette.ColorRole.Text, QColor(colors["text"]))
    theme_palette.setColor(QPalette.ColorRole.Button, QColor(colors["surfaceContainerHigh"]))
    theme_palette.setColor(QPalette.ColorRole.ButtonText, QColor(colors["text"]))
    theme_palette.setColor(QPalette.ColorRole.BrightText, QColor(colors["red"]))
    theme_palette.setColor(QPalette.ColorRole.Link, QColor(colors["blue"]))
    theme_palette.setColor(QPalette.ColorRole.Highlight, QColor(colors["blue"]))
    theme_palette.setColor(QPalette.ColorRole.HighlightedText, QColor(colors["crust"]))
    app.setPalette(theme_palette)

    app.setStyleSheet(f"""
        QWidget {{
            background: {colors['surface']};
            color: {colors['text']};
            font-family: "JetBrainsMono Nerd Font Propo", "JetBrainsMono Nerd Font", "Symbols Nerd Font", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans", Arial, sans-serif;
            font-size: 10pt;
        }}
        QMainWindow, QDialog {{
            background: {colors['surface']};
        }}

        /* Typography */
        QLabel#PageTitle {{
            font-size: 16pt;
            font-weight: 700;
            color: {colors['text']};
            padding-top: 4px;
            padding-bottom: 4px;
            min-height: 28px;
        }}
        QLabel#SectionTitle {{
            font-size: 12pt;
            font-weight: 650;
            color: {colors['text']};
            padding-top: 2px;
            padding-bottom: 2px;
        }}
        QLabel#Muted {{
            color: {colors['subtext']};
            font-size: 9.2pt;
        }}

        /* Navigation Drawer / Sidebar */
        QListWidget#Sidebar {{
            background: {colors['crust']};
            border: 1px solid {colors['outlineVariant']};
            border-radius: 14px;
            padding: 8px 6px;
        }}
        QListWidget#Sidebar::item {{
            padding: 10px 12px;
            margin: 2px 0px;
            border-radius: 10px;
            color: {colors['subtext']};
            font-weight: 550;
            font-size: 10pt;
            font-family: "JetBrainsMono Nerd Font Propo", "JetBrainsMono Nerd Font", "Symbols Nerd Font", sans-serif;
        }}
        QListWidget#Sidebar::item:hover {{
            background: {colors['surfaceContainerHigh']};
            color: {colors['text']};
        }}
        QListWidget#Sidebar::item:selected {{
            background: {colors['surface0']};
            color: {colors['blue']};
            font-weight: 700;
            border-left: 3px solid {colors['blue']};
        }}

        /* Material Cards */
        QFrame#Card {{
            background: {colors['surfaceContainer']};
            border: 1px solid {colors['outline']};
            border-radius: 14px;
        }}
        QFrame#NestedCard {{
            background: {colors['surfaceContainerHigh']};
            border: 1px solid {colors['surface0']};
            border-radius: 10px;
        }}
        QFrame#SettingRow {{
            background: transparent;
            border-radius: 10px;
            padding: 6px 8px;
        }}
        QFrame#SettingRow:hover {{
            background: {colors['surfaceContainerHigh']};
        }}

        /* Tab Widget (Material Pill segmented style) */
        QTabWidget::pane {{
            border: 1px solid {colors['outline']};
            border-radius: 12px;
            background: {colors['surfaceContainer']};
            padding: 12px;
            top: -1px;
        }}
        QTabBar::tab {{
            background: {colors['crust']};
            color: {colors['subtext']};
            padding: 8px 18px;
            margin-right: 6px;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            border: 1px solid {colors['outlineVariant']};
            border-bottom: none;
            font-weight: 600;
        }}
        QTabBar::tab:hover {{
            background: {colors['surfaceContainerHigh']};
            color: {colors['text']};
        }}
        QTabBar::tab:selected {{
            background: {colors['surfaceContainer']};
            color: {colors['blue']};
            border: 1px solid {colors['outline']};
            border-bottom: 2px solid {colors['blue']};
            font-weight: 700;
        }}

        /* Input Controls */
        QLineEdit, QSpinBox, QComboBox {{
            background: {colors['crust']};
            color: {colors['text']};
            border: 1px solid {colors['surface0']};
            border-radius: 8px;
            padding: 7px 10px;
            font-size: 9.5pt;
        }}
        QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
            border: 1px solid {colors['blue']};
            background: {colors['surfaceContainerHigh']};
        }}
        QLineEdit#SearchInput {{
            background: {colors['crust']};
            border: 1px solid {colors['surface0']};
            border-radius: 18px;
            padding: 8px 16px;
            font-size: 9.5pt;
        }}
        QLineEdit#SearchInput:focus {{
            border-color: {colors['blue']};
        }}
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 26px;
            border-left: none;
        }}
        QComboBox QAbstractItemView {{
            background: {colors['crust']};
            border: 1px solid {colors['surface0']};
            border-radius: 8px;
            selection-background-color: {colors['surface0']};
            selection-color: {colors['blue']};
            padding: 4px;
        }}
        QPlainTextEdit {{
            background: {colors['crust']};
            color: {colors['text']};
            border: 1px solid {colors['surface0']};
            border-radius: 8px;
            padding: 8px;
            font-family: JetBrains Mono, monospace;
            font-size: 9pt;
        }}

        /* Buttons */
        QPushButton {{
            background: {colors['surfaceContainerHigh']};
            color: {colors['text']};
            border: 1px solid {colors['surface0']};
            border-radius: 8px;
            padding: 8px 14px;
            font-weight: 600;
        }}
        QPushButton:hover {{
            background: {colors['surface0']};
            border-color: {colors['blue']};
            color: {colors['blue']};
        }}
        QPushButton:pressed {{
            background: {colors['surface1']};
        }}
        QPushButton:disabled {{
            background: {colors['surfaceContainer']};
            color: {colors['muted']};
            border: 1px solid {colors['outlineVariant']};
        }}
        QPushButton#Primary {{
            background: {colors['blue']};
            color: {colors['crust']};
            border: none;
            font-weight: 700;
        }}
        QPushButton#Primary:hover {{
            background: {colors['lavender']};
        }}
        QPushButton#Success {{
            background: {colors['green']};
            color: {colors['crust']};
            border: none;
            font-weight: 700;
        }}
        QPushButton#Danger {{
            background: {colors['red']};
            color: {colors['crust']};
            border: none;
            font-weight: 700;
        }}
        QPushButton#Outlined {{
            background: transparent;
            border: 1px solid {colors['surface0']};
            color: {colors['text']};
        }}
        QPushButton#Outlined:hover {{
            border-color: {colors['blue']};
            color: {colors['blue']};
        }}

        /* Sliders */
        QSlider::groove:horizontal {{
            height: 6px;
            background: {colors['surface0']};
            border-radius: 3px;
        }}
        QSlider::sub-page:horizontal {{
            background: {colors['blue']};
            border-radius: 3px;
        }}
        QSlider::handle:horizontal {{
            background: {colors['text']};
            border: 2px solid {colors['blue']};
            width: 16px;
            height: 16px;
            margin: -6px 0;
            border-radius: 9px;
        }}
        QSlider::handle:horizontal:hover {{
            background: {colors['lavender']};
            transform: scale(1.1);
        }}

        /* Checkboxes (Toggle switches) */
        QCheckBox {{
            spacing: 8px;
        }}
        QCheckBox::indicator {{
            width: 20px;
            height: 20px;
            border-radius: 6px;
            border: 1px solid {colors['surface1']};
            background: {colors['crust']};
        }}
        QCheckBox::indicator:hover {{
            border-color: {colors['blue']};
        }}
        QCheckBox::indicator:checked {{
            background: {colors['blue']};
            border-color: {colors['blue']};
        }}

        /* Modern Slim Scrollbar */
        QScrollBar:vertical {{
            background: transparent;
            width: 8px;
            margin: 0px;
        }}
        QScrollBar::handle:vertical {{
            background: {colors['surface0']};
            min-height: 24px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {colors['surface1']};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QScrollBar:horizontal {{
            background: transparent;
            height: 8px;
            margin: 0px;
        }}
        QScrollBar::handle:horizontal {{
            background: {colors['surface0']};
            min-width: 24px;
            border-radius: 4px;
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}

        /* Table & Lists */
        QTableWidget, QTableView {{
            background-color: {colors['crust']};
            alternate-background-color: {colors['surfaceContainerHigh']};
            color: {colors['text']};
            border: 1px solid {colors['outline']};
            border-radius: 8px;
            gridline-color: {colors['surfaceContainerHigh']};
            selection-background-color: {colors['surface0']};
            selection-color: {colors['blue']};
            outline: none;
        }}
        QTableWidget::item, QTableView::item {{
            color: {colors['text']};
            padding: 6px 8px;
            border-bottom: 1px solid {colors['surfaceContainerHigh']};
        }}
        QTableWidget::item:alternate, QTableView::item:alternate {{
            background-color: {colors['surfaceContainerHigh']};
            color: {colors['text']};
        }}
        QTableWidget::item:selected, QTableView::item:selected {{
            background-color: {colors['surface0']};
            color: {colors['blue']};
        }}
        QHeaderView {{
            background-color: {colors['surfaceContainerHigh']};
            border: none;
        }}
        QHeaderView::section {{
            background-color: {colors['surfaceContainerHigh']};
            color: {colors['subtext']};
            padding: 7px 10px;
            border: none;
            border-right: 1px solid {colors['surface0']};
            border-bottom: 1px solid {colors['outline']};
            font-weight: 650;
            font-size: 9pt;
        }}
        QTableCornerButton::section {{
            background-color: {colors['surfaceContainerHigh']};
            border: none;
        }}

        /* Progress Bar */
        QProgressBar {{
            background: {colors['surface0']};
            border: none;
            border-radius: 5px;
            height: 10px;
            text-align: right;
        }}
        QProgressBar::chunk {{
            background: {colors['blue']};
            border-radius: 5px;
        }}

        /* Dynamic Brand Typography */
        QLabel#BrandTitle {{
            font-size: 13pt;
            font-weight: 700;
            color: {colors['blue']};
        }}
        QLabel#BrandSubtitle {{
            font-size: 8.5pt;
            color: {colors['subtext']};
        }}
    """)
