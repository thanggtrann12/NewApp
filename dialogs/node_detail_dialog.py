from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QGroupBox, QLineEdit
)
from PyQt5.QtCore import Qt
from models.node import Node
from dialogs.crop_select_dialog import CropSelectDialog



class NodeDetailDialog(QDialog):
    def __init__(self, node: Node, crop_registry, parent=None):
        super().__init__(parent)
        self.node = node
        self.crop_registry = crop_registry
        if not hasattr(self.node, "pump_crop_map"):
            self.node.pump_crop_map = {}
        self.crop_labels = {}

        self.setWindowTitle("Node Configuration")
        self.setModal(True)
        self.resize(780, 500)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ==================================================
        # NODE INFO + NAME EDIT
        # ==================================================
        info_box = QGroupBox("Node Info")
        info_layout = QVBoxLayout(info_box)

        self.name_edit = QLineEdit(node.name)
        self.name_edit.setPlaceholderText("Node name (e.g. Greenhouse A)")
        self.name_edit.setMinimumHeight(36)

        info_layout.addWidget(QLabel("Name:"))
        info_layout.addWidget(self.name_edit)

        info_layout.addWidget(
            QLabel(
                f"<b>ID:</b> {node.id}<br>"
                f"<b>MAC:</b> {node.mac or '-'}<br>"
                f"<b>Pumps:</b> {node.pumps}"
            )
        )

        layout.addWidget(info_box)

        # ==================================================
        # PUMP → CROP CONFIG
        # ==================================================
        group = QGroupBox("Pump → Crop Mapping")
        group_layout = QVBoxLayout(group)

        if node.pumps <= 0:
            group_layout.addWidget(
                QLabel("Node not connected. No pump info.")
            )
        else:
            for i in range(node.pumps):
                row = QHBoxLayout()

                lbl = QLabel(f"Pump {i + 1}")

                crop_id = node.pump_crop_map.get(i)
                crop = self.crop_registry.get(crop_id)
                crop_name = crop.name if crop else "Not set"

                crop_lbl = QLabel(crop_name)
                crop_lbl.setMinimumWidth(160)

                btn = QPushButton("Select Crop")
                btn.setMinimumHeight(36)
                btn.clicked.connect(
                    lambda _, p=i: self.select_crop(p)
                )

                self.crop_labels[i] = crop_lbl

                row.addWidget(lbl)
                row.addWidget(crop_lbl, 1)
                row.addWidget(btn)

                group_layout.addLayout(row)

        layout.addWidget(group, 1)

        # ==================================================
        # BUTTONS
        # ==================================================
        btns = QHBoxLayout()
        btns.addStretch(1)

        close = QPushButton("Close")
        save = QPushButton("Save")
        save.setObjectName("DetailButton")
        save.setMinimumHeight(40)

        close.clicked.connect(self.reject)
        save.clicked.connect(self.on_save)

        btns.addWidget(close)
        btns.addWidget(save)

        layout.addLayout(btns)

    # ==================================================
    # ACTIONS
    # ==================================================
    def select_crop(self, pump_index: int):
        dlg = CropSelectDialog(self.crop_registry, self)
        if dlg.exec_():
            crop = dlg.selected_crop        # ✅ dict
            crop_id = crop.id               # ✅ string

            self.node.pump_crop_map[pump_index] = crop_id

            crop_name = crop.name
            self.crop_labels[pump_index].setText(crop_name)

    def on_save(self):
        self.node.name = self.name_edit.text().strip()
        self.accept()
