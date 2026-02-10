from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QFormLayout, QLineEdit, QPushButton
)
from PyQt5.QtCore import Qt
from models.node import Node


class AddNodeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle(self.tr("Add Node"))
        self.setObjectName("Card")
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # =========================
        # FORM
        # =========================
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText(
            self.tr("Optional (e.g. Greenhouse A)")
        )

        form.addRow(self.tr("Name:"), self.name_edit)
        layout.addLayout(form)

        # =========================
        # BUTTONS
        # =========================
        btns = QHBoxLayout()
        cancel = QPushButton(self.tr("Cancel"))
        ok = QPushButton(self.tr("Add"))
        ok.setObjectName("DetailButton")
        ok.setDefault(True)

        cancel.clicked.connect(self.reject)
        ok.clicked.connect(self.accept)

        btns.addStretch(1)
        btns.addWidget(cancel)
        btns.addWidget(ok)
        layout.addLayout(btns)

    def result_node(self) -> Node:
        return Node.new(
            name=self.name_edit.text().strip()
        )
