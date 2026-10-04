"""Keybindings and keyboard shortcuts manager view.

Displays the complete categorized catalog of 80+ shortcuts with physical keycap badges,
live search and category filter, and modal Add/Edit dialogs with safety backups and
instant Qtile IPC reload.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from qtile_settings.adapters import keybindings, qtile
from qtile_settings.ui.common import card, create_keycap, create_pill_badge


class KeybindingDialog(QDialog):
    """Modal dialog for editing or adding a Qtile keybinding."""

    def __init__(self, item: keybindings.KeybindingItem | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Edit Keybinding" if item else "Add New Keybinding")
        self.setMinimumWidth(540)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        form = QFormLayout()
        form.setSpacing(10)

        # Modifiers
        mods_box = QHBoxLayout()
        mods_box.setSpacing(8)
        self.chk_mod = QCheckBox("Super (MOD)")
        self.chk_shift = QCheckBox("Shift")
        self.chk_ctrl = QCheckBox("Control")
        self.chk_alt = QCheckBox("Alt (mod1)")

        if item:
            self.chk_mod.setChecked(any(m in ("MOD", "mod4") for m in item.modifiers))
            self.chk_shift.setChecked("shift" in item.modifiers)
            self.chk_ctrl.setChecked("control" in item.modifiers)
            self.chk_alt.setChecked(any(m in ("mod1", "alt") for m in item.modifiers))
        else:
            self.chk_mod.setChecked(True)

        mods_box.addWidget(self.chk_mod)
        mods_box.addWidget(self.chk_shift)
        mods_box.addWidget(self.chk_ctrl)
        mods_box.addWidget(self.chk_alt)
        mods_box.addStretch()
        form.addRow("Modifiers:", mods_box)

        # Key
        self.key_edit = QLineEdit(item.key if item else "Return")
        self.key_edit.setPlaceholderText("e.g. Return, space, q, d, Left, F2")
        form.addRow("Key Name:", self.key_edit)

        # Action Type
        self.action_type = QComboBox()
        self.action_type.addItems([
            "Spawn Command (lazy.spawn)",
            "Kill Window (lazy.window.kill)",
            "Restart Qtile (lazy.restart)",
            "Next Layout (lazy.next_layout)",
            "Previous Layout (lazy.prev_layout)",
            "Toggle Fullscreen (lazy.window.toggle_fullscreen)",
            "Toggle Floating (lazy.window.toggle_floating)",
            "Toggle Maximize (lazy.window.toggle_maximize)",
            "Toggle Minimize (lazy.window.toggle_minimize)",
            "Custom Lazy Function",
        ])
        form.addRow("Action Type:", self.action_type)

        # Command / Parameter
        self.cmd_edit = QLineEdit()
        self.cmd_edit.setPlaceholderText("e.g. alacritty, thunar, or full command")
        if item:
            if "lazy.spawn(" in item.action:
                raw = item.action.replace("lazy.spawn(", "").rstrip(")")
                self.cmd_edit.setText(raw.strip("'\""))
                self.action_type.setCurrentIndex(0)
            elif "lazy.window.kill" in item.action:
                self.action_type.setCurrentIndex(1)
            elif "lazy.restart" in item.action:
                self.action_type.setCurrentIndex(2)
            elif "lazy.next_layout" in item.action:
                self.action_type.setCurrentIndex(3)
            elif "lazy.prev_layout" in item.action:
                self.action_type.setCurrentIndex(4)
            elif "toggle_fullscreen" in item.action:
                self.action_type.setCurrentIndex(5)
            elif "toggle_floating" in item.action:
                self.action_type.setCurrentIndex(6)
            elif "toggle_maximize" in item.action:
                self.action_type.setCurrentIndex(7)
            elif "toggle_minimize" in item.action:
                self.action_type.setCurrentIndex(8)
            else:
                self.action_type.setCurrentIndex(9)
                self.cmd_edit.setText(item.action)

        form.addRow("Command / Target:", self.cmd_edit)

        # Description
        self.desc_edit = QLineEdit(item.description if item else "")
        self.desc_edit.setPlaceholderText("Brief human-readable label")
        form.addRow("Description:", self.desc_edit)

        # Category
        self.cat_combo = QComboBox()
        self.cat_combo.addItems([
            "Applications & Launchers",
            "Window Management",
            "Layout & Navigation",
            "Workspaces",
            "Hardware & Media",
            "Screenshots",
            "Custom & Other",
        ])
        if item:
            idx = self.cat_combo.findText(item.category)
            if idx >= 0:
                self.cat_combo.setCurrentIndex(idx)
        form.addRow("Category:", self.cat_combo)

        layout.addLayout(form)

        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        ok_btn = btn_box.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn:
            ok_btn.setObjectName("Primary")
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def get_data(self) -> dict[str, Any]:
        mods = []
        if self.chk_mod.isChecked():
            mods.append("MOD")
        if self.chk_shift.isChecked():
            mods.append("shift")
        if self.chk_ctrl.isChecked():
            mods.append("control")
        if self.chk_alt.isChecked():
            mods.append("mod1")

        action_idx = self.action_type.currentIndex()
        cmd = self.cmd_edit.text().strip()
        if action_idx == 0:
            if cmd.startswith(("TERMINAL", "SCRIPTS", "LAUNCHER", "f'", 'f"')):
                action_str = f"lazy.spawn({cmd})"
            else:
                action_str = f"lazy.spawn({cmd!r})"
        elif action_idx == 1:
            action_str = "lazy.window.kill()"
        elif action_idx == 2:
            action_str = "lazy.restart()"
        elif action_idx == 3:
            action_str = "lazy.next_layout()"
        elif action_idx == 4:
            action_str = "lazy.prev_layout()"
        elif action_idx == 5:
            action_str = "lazy.window.toggle_fullscreen()"
        elif action_idx == 6:
            action_str = "lazy.window.toggle_floating()"
        elif action_idx == 7:
            action_str = "lazy.window.toggle_maximize()"
        elif action_idx == 8:
            action_str = "lazy.window.toggle_minimize()"
        else:
            action_str = cmd or "lazy.restart()"

        desc = self.desc_edit.text().strip() or self.action_type.currentText()
        cat = self.cat_combo.currentText()
        key_name = self.key_edit.text().strip() or "Return"

        return {
            "modifiers": mods,
            "key": key_name,
            "action": action_str,
            "description": desc,
            "category": cat,
        }


CATEGORY_COLORS: dict[str, str] = {
    "Applications & Launchers": "#89b4fa",
    "Window Management": "#cba6f7",
    "Layout & Navigation": "#94e2d5",
    "Workspaces": "#fab387",
    "Hardware & Media": "#a6e3a1",
    "Screenshots": "#f9e2af",
    "Custom & Other": "#a6adc8",
}


class KeybindingsPage(QWidget):
    """Graphical shortcut manager and editor for Qtile-Con."""

    def __init__(self):
        super().__init__()
        self.items: list[keybindings.KeybindingItem] = []
        self.filtered_items: list[keybindings.KeybindingItem] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        # Header Title & Description
        header = QVBoxLayout()
        header.setSpacing(8)

        title_col = QVBoxLayout()
        title_col.setSpacing(3)
        title = QLabel("Keybindings & Shortcuts")
        title.setObjectName("PageTitle")
        title.setWordWrap(True)
        title_col.addWidget(title)

        desc = QLabel("Comprehensive keyboard shortcut manager. Edits are safely written to qtile_config/keys.py.")
        desc.setObjectName("Muted")
        desc.setWordWrap(True)
        title_col.addWidget(desc)
        header.addLayout(title_col)

        # Action Toolbar Row
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.btn_add = QPushButton("󰐕 Add Shortcut")
        self.btn_add.clicked.connect(self.add_keybinding)
        toolbar.addWidget(self.btn_add)

        self.btn_save = QPushButton("󰆓 Save to keys.py")
        self.btn_save.setObjectName("Primary")
        self.btn_save.clicked.connect(self.save_changes)
        toolbar.addWidget(self.btn_save)

        self.btn_reload = QPushButton("󰑐 Reload Qtile")
        self.btn_reload.clicked.connect(self.reload_qtile)
        toolbar.addWidget(self.btn_reload)

        toolbar.addStretch()
        header.addLayout(toolbar)

        layout.addLayout(header)

        # Filter & Search bar card
        _, filter_box = card("Shortcut Catalog", "Search and filter keybindings by key, modifier, or category", icon="󰌌")

        search_row = QHBoxLayout()
        search_row.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("SearchInput")
        self.search_input.setPlaceholderText("  Search shortcuts (e.g. Return, Super, thunar, volume)...")
        self.search_input.textChanged.connect(self.apply_filter)
        search_row.addWidget(self.search_input, 1)

        self.cat_filter = QComboBox()
        self.cat_filter.addItem("All Categories")
        self.cat_filter.addItems([
            "Applications & Launchers",
            "Window Management",
            "Layout & Navigation",
            "Workspaces",
            "Hardware & Media",
            "Screenshots",
            "Custom & Other",
        ])
        self.cat_filter.currentIndexChanged.connect(self.apply_filter)
        search_row.addWidget(self.cat_filter)

        filter_box.addLayout(search_row)

        # Table of Keybindings
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Combination", "Description", "Action / Target", "Category", "Actions"])
        self.table.horizontalHeader().setMinimumSectionSize(90)
        for col_idx, width in enumerate([170, 220, 170, 200, 140]):
            self.table.horizontalHeader().setSectionResizeMode(col_idx, QHeaderView.ResizeMode.Interactive)
            self.table.setColumnWidth(col_idx, width)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(42)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        filter_box.addWidget(self.table)

        # Status footer
        status_row = QHBoxLayout()
        self.status_label = QLabel("Loading shortcuts...")
        self.status_label.setStyleSheet("color: #a6adc8; font-weight: 500;")
        status_row.addWidget(self.status_label)
        status_row.addStretch()

        filter_box.addLayout(status_row)
        layout.addWidget(_)

        self.load_keybindings()

    def load_keybindings(self):
        try:
            self.items = keybindings.read_keybindings()
            self.status_label.setText(f"Loaded {len(self.items)} shortcuts from keys.py")
            self.apply_filter()
        except (OSError, ValueError, SyntaxError) as e:
            self.status_label.setText(f"Error loading keys.py: {e}")

    def apply_filter(self):
        query = self.search_input.text().strip().lower()
        selected_cat = self.cat_filter.currentText()

        self.filtered_items = []
        for item in self.items:
            if selected_cat != "All Categories" and item.category != selected_cat:
                continue
            if query:
                match = (
                    query in item.display_combo.lower()
                    or query in item.key.lower()
                    or query in item.description.lower()
                    or query in item.action.lower()
                    or query in item.category.lower()
                )
                if not match:
                    continue
            self.filtered_items.append(item)

        self.populate_table()

    def populate_table(self):
        self.table.setRowCount(len(self.filtered_items))

        for row_idx, item in enumerate(self.filtered_items):
            # Key combination widget with hardware keycaps
            combo_widget = QWidget()
            combo_layout = QHBoxLayout(combo_widget)
            combo_layout.setContentsMargins(4, 2, 4, 2)
            combo_layout.setSpacing(3)

            for mod in item.modifiers:
                mod_name = keybindings.MOD_DISPLAY.get(mod, mod.capitalize())
                combo_layout.addWidget(create_keycap(mod_name, is_mod=True))

            key_label = item.key
            if key_label == "Return":
                key_label = "Enter"
            combo_layout.addWidget(create_keycap(key_label))
            combo_layout.addStretch()
            self.table.setCellWidget(row_idx, 0, combo_widget)

            # Description with icon
            desc_text = f"{item.icon}  {item.description}" if item.icon else item.description
            desc_item = QTableWidgetItem(desc_text)
            desc_item.setFlags(desc_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            desc_item.setForeground(QColor("#cdd6f4"))
            self.table.setItem(row_idx, 1, desc_item)

            # Clean action display with full tooltip
            clean_action = item.action
            if clean_action.startswith("lazy.spawn(") and clean_action.endswith(")"):
                inner = clean_action[len("lazy.spawn("):-1].strip("'\"")
                if "SCRIPTS" in inner:
                    inner = inner.replace("f'{SCRIPTS}/", "").replace('f"{SCRIPTS}/', "").replace("{SCRIPTS}/", "")
                    if inner.endswith(("'", '"')):
                        inner = inner[:-1]
                clean_action = inner

            action_item = QTableWidgetItem(clean_action)
            action_item.setToolTip(item.raw_code or item.action)
            action_item.setFlags(action_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            action_item.setForeground(QColor("#a6adc8"))
            act_font = action_item.font()
            act_font.setFamily("JetBrainsMono Nerd Font")
            act_font.setPointSize(8.5)
            action_item.setFont(act_font)
            self.table.setItem(row_idx, 2, action_item)

            # Category Pill with dedicated accent color
            cat_widget = QWidget()
            cat_layout = QHBoxLayout(cat_widget)
            cat_layout.setContentsMargins(4, 2, 4, 2)
            cat_color = CATEGORY_COLORS.get(item.category, "#89b4fa")
            cat_badge = create_pill_badge(item.category, color=cat_color, bg="#181825")
            cat_layout.addWidget(cat_badge)
            self.table.setCellWidget(row_idx, 3, cat_widget)

            # Action Buttons
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 3, 4, 3)
            btn_layout.setSpacing(6)

            btn_edit = QPushButton("󰏫 Edit")
            btn_edit.setStyleSheet("padding: 4px 10px; font-size: 8.5pt; font-weight: 600;")
            btn_edit.clicked.connect(lambda _, it=item: self.edit_keybinding(it))
            btn_layout.addWidget(btn_edit)

            btn_del = QPushButton("󰆴")
            btn_del.setToolTip("Delete this shortcut")
            btn_del.setStyleSheet("padding: 4px 8px; font-size: 9pt; color: #f38ba8;")
            btn_del.clicked.connect(lambda _, it=item: self.delete_keybinding(it))
            btn_layout.addWidget(btn_del)

            self.table.setCellWidget(row_idx, 4, btn_widget)

    def edit_keybinding(self, item: keybindings.KeybindingItem):
        dialog = KeybindingDialog(item, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            item.modifiers = data["modifiers"]
            item.key = data["key"]
            item.action = data["action"]
            item.description = data["description"]
            item.category = data["category"]
            self.status_label.setText(f"Modified '{item.display_combo}'. Click 'Save to keys.py' to commit.")
            self.apply_filter()

    def add_keybinding(self):
        dialog = KeybindingDialog(None, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            new_item = keybindings.KeybindingItem(
                id=keybindings.uuid.uuid4().hex[:8],
                modifiers=data["modifiers"],
                key=data["key"],
                action=data["action"],
                description=data["description"],
                category=data["category"],
            )
            self.items.append(new_item)
            self.status_label.setText(f"Added shortcut '{new_item.display_combo}'. Click 'Save to keys.py' to commit.")
            self.apply_filter()

    def delete_keybinding(self, item: keybindings.KeybindingItem):
        reply = QMessageBox.question(
            self,
            "Delete Keybinding",
            f"Are you sure you want to remove '{item.display_combo}' ({item.description})?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.items = [it for it in self.items if it.id != item.id]
            self.status_label.setText(f"Deleted shortcut '{item.display_combo}'. Click 'Save to keys.py' to commit.")
            self.apply_filter()

    def save_changes(self):
        try:
            path = keybindings.save_keybindings(self.items)
            self.status_label.setText(f"Saved {len(self.items)} shortcuts to {path.name}")
            ok, msg = qtile.reload_qtile()
            if ok:
                QMessageBox.information(self, "Success", f"Keybindings saved and Qtile reloaded successfully.\n{msg}")
            else:
                QMessageBox.warning(self, "Saved", f"Keybindings saved to keys.py, but reload notification: {msg}")
        except (OSError, ValueError, SyntaxError) as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save keybindings:\n{e}")

    def reload_qtile(self):
        ok, msg = qtile.reload_qtile()
        self.status_label.setText(f"Reload: {msg}")
        if not ok:
            QMessageBox.warning(self, "Qtile Reload", msg)
