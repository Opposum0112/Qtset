"""CLI entry point for Qtile Settings & Command Center.

Handles command-line arguments, boots the PySide6 Qt application instance, loads
the active desktop color scheme dynamically, and displays either the primary
MainWindow control center or the lightweight QuickSettings floating popup.
"""

from __future__ import annotations

import argparse
import sys

from PySide6.QtWidgets import QApplication

from qtile_settings.adapters import themes
from qtile_settings.theme import apply_theme
from qtile_settings.ui.main_window import MainWindow
from qtile_settings.ui.quick_settings import QuickSettings


def main() -> int:
    """Parse CLI options, configure the Qt application context, and launch the GUI.

    Returns:
        Exit code returned by Qt's QApplication event loop.
    """
    parser = argparse.ArgumentParser(
        description="Qtile Settings & Session Command Center",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Launch the compact always-on-top Quick Settings popup instead of the full center",
    )
    args = parser.parse_args()

    # Initialize QApplication context with explicit application naming
    app = QApplication(sys.argv)
    app.setApplicationName("Qtile Settings")
    app.setQuitOnLastWindowClosed(True)

    # Automatically synchronize theme tokens with the active Qtile desktop palette
    palette = themes.get_current_theme_palette()
    apply_theme(app, palette)

    # Launch requested interface window mode
    window = QuickSettings() if args.quick else MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
