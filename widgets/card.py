# widgets/card.py
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtWidgets import QGraphicsDropShadowEffect

from models.node import Node

class NodeCard(QFrame):
    removeRequested = pyqtSignal(str)     # node_id
    detailRequested = pyqtSignal(str)     # node_id

    def __init__(self, node: Node, parent=None):
        super().__init__(parent)
        self.node = node
        self.setObjectName("Card")
        self.setFixedSize(360, 170)  # phù hợp màn 800x480, có thể chỉnh

        # Shadow nhẹ
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(18)
        shadow.setColor(QColor(0, 0, 0, 120))
        shadow.setOffset(0, 3)
        self.setGraphicsEffect(shadow)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(12)

        # Header: "1 Crops"  +  close (x)
        header = QHBoxLayout()
        header.setContentsMargins(0,0,0,0)
        header.setSpacing(0)

        self.crops_lbl = QLabel(f"{self.node.crops} Crops")
        self.crops_lbl.setObjectName("CardTitle")
        self.crops_lbl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        close_btn = QPushButton("×")  # dùng ký tự Unicode
        close_btn.setObjectName("CloseButton")
        close_btn.setFixedSize(28, 28)
        close_btn.clicked.connect(lambda: self.removeRequested.emit(self.node.id))

        header.addWidget(self.crops_lbl, 1)
        header.addWidget(close_btn, 0, Qt.AlignRight)

        # Body: MAC
        self.mac_lbl = QLabel(f"MAC: {self.node.mac or '-'}")
        self.mac_lbl.setObjectName("CardSub")
        self.mac_lbl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        # Footer: DETAIL button (full width)
        detail_btn = QPushButton("DETAIL")
        detail_btn.setObjectName("DetailButton")
        detail_btn.setFixedHeight(36)
        detail_btn.clicked.connect(lambda: self.detailRequested.emit(self.node.id))

        outer.addLayout(header)
        outer.addWidget(self.mac_lbl)
        outer.addStretch(1)
        outer.addWidget(detail_btn)

    def update_from(self, node: Node):
        self.node = node
        self.crops_lbl.setText(f"{node.crops} Crops")
        self.mac_lbl.setText(f"MAC: {node.mac or '-'}")