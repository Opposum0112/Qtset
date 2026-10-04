"""Reusable UI components and Material 3 design primitives.

Provides standardized cards, squircle icon badges, status pills, physical hardware keycaps,
and setting rows (SliderSettingRow, ToggleSettingRow, SelectionSettingRow, StringSettingRow,
ColorSettingRow, PathSettingRow, ActionSettingRow).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)


def create_icon_badge(icon: str, color: str = "#89b4fa", bg: str = "#252538", size: int = 36) -> QLabel:
    """Create a Material-styled squircle icon badge."""
    lbl = QLabel(icon)
    lbl.setFixedSize(size, size)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setStyleSheet(
        f"background: {bg}; border: 1px solid #363a4f; border-radius: {size // 4}px; "
        f"color: {color}; font-family: 'Symbols Nerd Font', 'JetBrainsMono Nerd Font', monospace; "
        f"font-size: 13pt; font-weight: bold;"
    )
    return lbl


def create_pill_badge(text: str, color: str = "#89b4fa", bg: str = "#252538") -> QLabel:
    """Create a rounded status pill badge."""
    lbl = QLabel(text)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setStyleSheet(
        f"background: {bg}; border: 1px solid #363a4f; border-radius: 12px; "
        f"color: {color}; font-family: 'JetBrainsMono Nerd Font Propo', 'JetBrainsMono Nerd Font', sans-serif; "
        f"font-weight: 600; font-size: 8.5pt; padding: 3px 10px;"
    )
    return lbl


def create_keycap(text: str, is_mod: bool = False) -> QLabel:
    """Create a keyboard keycap badge styled like physical hardware keycaps."""
    lbl = QLabel(text)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    bg = "#2e324a" if is_mod else "#1e1e2e"
    color = "#b4befe" if is_mod else "#cdd6f4"
    border = "#45475a"
    lbl.setStyleSheet(
        f"background: {bg}; border: 1px solid {border}; border-bottom: 2px solid #585b70; "
        f"border-radius: 5px; color: {color}; font-family: 'JetBrainsMono Nerd Font', 'JetBrains Mono', monospace; font-weight: 700; "
        "font-size: 8.5pt; padding: 2px 7px; margin: 1px;"
    )
    return lbl


def card(
    title: str,
    description: str = "",
    icon: str = "",
    extra_header: QWidget | None = None,
) -> tuple[QFrame, QVBoxLayout]:
    """Create a Material 3 card container with squircle icon, title, description, and content layout."""
    frame = QFrame()
    frame.setObjectName("Card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(12)

    header = QHBoxLayout()
    header.setSpacing(12)

    if icon:
        header.addWidget(create_icon_badge(icon, color="#89b4fa"))

    text_box = QVBoxLayout()
    text_box.setSpacing(2)
    heading = QLabel(title)
    heading.setObjectName("SectionTitle")
    heading.setWordWrap(True)
    text_box.addWidget(heading)

    if description:
        detail = QLabel(description)
        detail.setWordWrap(True)
        detail.setObjectName("Muted")
        text_box.addWidget(detail)
    header.addLayout(text_box, 1)

    if extra_header:
        header.addWidget(extra_header)

    layout.addLayout(header)

    sep = QFrame()
    sep.setFrameShape(QFrame.Shape.HLine)
    sep.setStyleSheet("background: #313244; max-height: 1px; margin-top: 2px; margin-bottom: 4px;")
    layout.addWidget(sep)

    return frame, layout


class SliderSettingRow(QWidget):
    """A graphical setting row featuring an icon, label, live horizontal slider, and value badge."""

    def __init__(
        self,
        label: str,
        min_val: int,
        max_val: int,
        current_val: int,
        unit: str = "",
        icon: str = "",
        description: str = "",
        on_change: Callable[[int], None] | None = None,
    ):
        super().__init__()
        self.unit = unit
        self.on_change = on_change

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 6, 4, 6)
        layout.setSpacing(12)

        if icon:
            layout.addWidget(create_icon_badge(icon, color="#b4befe", size=32))

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        lbl = QLabel(label)
        lbl.setStyleSheet("font-weight: 600; color: #cdd6f4;")
        text_col.addWidget(lbl)
        if description:
            desc = QLabel(description)
            desc.setWordWrap(True)
            desc.setObjectName("Muted")
            text_col.addWidget(desc)
        layout.addLayout(text_col)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(min_val, max_val)
        self.slider.setValue(current_val)
        self.slider.setMinimumWidth(110)
        layout.addWidget(self.slider, 1)

        self.badge = QLabel(f"{current_val} {unit}".strip())
        self.badge.setStyleSheet(
            "background: #11111b; border: 1px solid #363a4f; border-radius: 8px; "
            "padding: 4px 10px; font-weight: 700; color: #89b4fa; min-width: 58px; text-align: center;"
        )
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.badge)

        self.slider.valueChanged.connect(self._handle_change)

    def _handle_change(self, val: int):
        self.badge.setText(f"{val} {self.unit}".strip())
        if self.on_change:
            self.on_change(val)

    def value(self) -> int:
        return self.slider.value()

    def setValue(self, val: int):
        self.slider.setValue(val)


class ToggleSettingRow(QWidget):
    """A Material-styled setting row with title, description, and toggle switch."""

    def __init__(
        self,
        title: str,
        description: str = "",
        checked: bool = False,
        icon: str = "",
        on_toggle: Callable[[bool], None] | None = None,
    ):
        super().__init__()
        self.on_toggle = on_toggle

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 6, 4, 6)
        layout.setSpacing(12)

        if icon:
            layout.addWidget(create_icon_badge(icon, color="#cba6f7", size=32))

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        head = QLabel(title)
        head.setStyleSheet("font-weight: 600; color: #cdd6f4;")
        text_col.addWidget(head)

        if description:
            desc = QLabel(description)
            desc.setWordWrap(True)
            desc.setObjectName("Muted")
            text_col.addWidget(desc)
        layout.addLayout(text_col, 1)

        self.checkbox = QCheckBox()
        self.checkbox.setChecked(checked)
        if on_toggle:
            self.checkbox.toggled.connect(on_toggle)
        layout.addWidget(self.checkbox)

    def isChecked(self) -> bool:
        return self.checkbox.isChecked()

    def setChecked(self, checked: bool):
        self.checkbox.setChecked(checked)


class SelectionSettingRow(QWidget):
    """A Material-styled dropdown selection setting row."""

    def __init__(
        self,
        title: str,
        options: list[tuple[str, Any]] | list[str],
        current_val: Any = None,
        description: str = "",
        icon: str = "",
        on_change: Callable[[Any], None] | None = None,
    ):
        super().__init__()
        self.on_change = on_change

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 6, 4, 6)
        layout.setSpacing(12)

        if icon:
            layout.addWidget(create_icon_badge(icon, color="#89b4fa", size=32))

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        head = QLabel(title)
        head.setStyleSheet("font-weight: 600; color: #cdd6f4;")
        text_col.addWidget(head)

        if description:
            desc = QLabel(description)
            desc.setWordWrap(True)
            desc.setObjectName("Muted")
            text_col.addWidget(desc)
        layout.addLayout(text_col, 1)

        self.combo = QComboBox()
        self.combo.setMinimumWidth(180)

        for opt in options:
            if isinstance(opt, tuple):
                label, val = opt
                self.combo.addItem(label, val)
            else:
                self.combo.addItem(str(opt), opt)

        if current_val is not None:
            idx = self.combo.findData(current_val)
            if idx >= 0:
                self.combo.setCurrentIndex(idx)
            else:
                idx = self.combo.findText(str(current_val))
                if idx >= 0:
                    self.combo.setCurrentIndex(idx)

        self.combo.currentIndexChanged.connect(self._handle_change)
        layout.addWidget(self.combo)

    def _handle_change(self, index: int):
        val = self.combo.currentData()
        if val is None:
            val = self.combo.currentText()
        if self.on_change:
            self.on_change(val)

    def current_value(self) -> Any:
        val = self.combo.currentData()
        return val if val is not None else self.combo.currentText()

    def setValue(self, val: Any):
        idx = self.combo.findData(val)
        if idx >= 0:
            self.combo.setCurrentIndex(idx)
        else:
            idx = self.combo.findText(str(val))
            if idx >= 0:
                self.combo.setCurrentIndex(idx)


class StringSettingRow(QWidget):
    """A Material-styled text entry setting row with optional file/directory browse action."""

    def __init__(
        self,
        title: str,
        current_val: str = "",
        placeholder: str = "",
        description: str = "",
        icon: str = "",
        on_change: Callable[[str], None] | None = None,
        browse_dir: bool = False,
        browse_file: bool = False,
    ):
        super().__init__()
        self.on_change = on_change
        self.browse_dir = browse_dir
        self.browse_file = browse_file

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 6, 4, 6)
        layout.setSpacing(12)

        if icon:
            layout.addWidget(create_icon_badge(icon, color="#a6e3a1", size=32))

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        head = QLabel(title)
        head.setStyleSheet("font-weight: 600; color: #cdd6f4;")
        text_col.addWidget(head)

        if description:
            desc = QLabel(description)
            desc.setWordWrap(True)
            desc.setObjectName("Muted")
            text_col.addWidget(desc)
        layout.addLayout(text_col, 1)

        self.edit = QLineEdit(current_val)
        self.edit.setPlaceholderText(placeholder)
        self.edit.setMinimumWidth(180)
        self.edit.textChanged.connect(self._handle_change)
        layout.addWidget(self.edit)

        if browse_dir:
            btn = QPushButton("󰉋 Browse...")
            btn.clicked.connect(self._browse_dir)
            layout.addWidget(btn)
        elif browse_file:
            btn = QPushButton("󰈔 Select...")
            btn.clicked.connect(self._browse_file)
            layout.addWidget(btn)

    def _handle_change(self, text: str):
        if self.on_change:
            self.on_change(text)

    def _browse_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Directory", self.edit.text())
        if folder:
            self.edit.setText(folder)

    def _browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File", self.edit.text())
        if file_path:
            self.edit.setText(file_path)

    def text(self) -> str:
        return self.edit.text()

    def setText(self, text: str):
        self.edit.setText(text)


class ColorSettingRow(QWidget):
    """A Material-styled color picker row with live color swatch."""

    def __init__(
        self,
        title: str,
        current_hex: str = "#89b4fa",
        description: str = "",
        icon: str = "",
        on_change: Callable[[str], None] | None = None,
    ):
        super().__init__()
        self.color_hex = current_hex
        self.on_change = on_change

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 6, 4, 6)
        layout.setSpacing(12)

        if icon:
            layout.addWidget(create_icon_badge(icon, color="#fab387", size=32))

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        head = QLabel(title)
        head.setStyleSheet("font-weight: 600; color: #cdd6f4;")
        text_col.addWidget(head)

        if description:
            desc = QLabel(description)
            desc.setWordWrap(True)
            desc.setObjectName("Muted")
            text_col.addWidget(desc)
        layout.addLayout(text_col, 1)

        self.btn = QPushButton(self.color_hex)
        self.btn.setFixedWidth(110)
        self._update_swatch()
        self.btn.clicked.connect(self._pick_color)
        layout.addWidget(self.btn)

    def _update_swatch(self):
        self.btn.setText(self.color_hex)
        self.btn.setStyleSheet(
            f"background: {self.color_hex}; color: #11111b; font-weight: 700; "
            "border: 1px solid #363a4f; border-radius: 8px; padding: 6px 12px;"
        )

    def _pick_color(self):
        col = QColorDialog.getColor(QColor(self.color_hex), self, "Select Color")
        if col.isValid():
            self.color_hex = col.name()
            self._update_swatch()
            if self.on_change:
                self.on_change(self.color_hex)


class ActionSettingRow(QWidget):
    """A Material-styled action button row."""

    def __init__(
        self,
        title: str,
        button_label: str = "Execute",
        description: str = "",
        icon: str = "",
        on_click: Callable[[], None] | None = None,
        primary: bool = False,
    ):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 6, 4, 6)
        layout.setSpacing(12)

        if icon:
            layout.addWidget(create_icon_badge(icon, color="#89b4fa", size=32))

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        head = QLabel(title)
        head.setStyleSheet("font-weight: 600; color: #cdd6f4;")
        text_col.addWidget(head)

        if description:
            desc = QLabel(description)
            desc.setWordWrap(True)
            desc.setObjectName("Muted")
            text_col.addWidget(desc)
        layout.addLayout(text_col, 1)

        self.btn = QPushButton(button_label)
        if primary:
            self.btn.setObjectName("Primary")
        if on_click:
            self.btn.clicked.connect(on_click)
        layout.addWidget(self.btn)
