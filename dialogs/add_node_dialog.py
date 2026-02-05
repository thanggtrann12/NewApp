# dialogs/add_node_dialog.py
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QSpinBox,
    QPushButton
)
from PyQt5.QtCore import Qt
from models.node import Node

class AddNodeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Node")
        self.setObjectName("Card")  # reuse style card
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setFormAlignment(Qt.AlignTop)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Optional")
        self.crops_spin = QSpinBox()
        self.crops_spin.setRange(0, 999)
        self.crops_spin.setValue(1)

        self.mac_edit = QLineEdit()
        self.mac_edit.setPlaceholderText("AA:BB:CC:DD:EE:FF")

        form.addRow("Name:", self.name_edit)
        form.addRow("Crops:", self.crops_spin)
        form.addRow("MAC:", self.mac_edit)

        layout.addLayout(form)

        # Buttons
        btns = QHBoxLayout()
        cancel = QPushButton("Cancel")
        ok = QPushButton("Add")
        ok.setObjectName("DetailButton")  # style giống DETAIL
        ok.setDefault(True)

        cancel.clicked.connect(self.reject)
        ok.clicked.connect(self.accept)

        btns.addStretch(1)
        btns.addWidget(cancel)
        btns.addWidget(ok)
        layout.addLayout(btns)

    def result_node(self) -> Node:
        return Node.new(
            crops=int(self.crops_spin.value()),
            mac=self.mac_edit.text().strip(),
            name=self.name_edit.text().strip()
        )