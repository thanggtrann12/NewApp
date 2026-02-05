# widgets/card_grid.py
from typing import List
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QPushButton, QLabel, QScrollArea, QMessageBox
)

from models.node import Node
from models.store import NodeStore
from .card import NodeCard
from dialogs.add_node_dialog import AddNodeDialog

class CardGrid(QWidget):
    """
    - Hiển thị NodeCard theo lưới (mặc định 2 cột).
    - Có nút + ADD NODE dưới cùng (trải rộng).
    - Tự reflow khi resize.
    """
    def __init__(self, store: NodeStore, parent=None):
        super().__init__(parent)
        self.store = store
        self.columns = 2  # số cột mục tiêu
        self.cards: List[NodeCard] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        # Tiêu đề
        title = QLabel("IoT Irrigation System")
        title.setObjectName("AppTitle")
        root.addWidget(title, 0, Qt.AlignLeft)

        # Scroll area để chứa grid
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(self.scroll.NoFrame)
        root.addWidget(self.scroll, 1)

        # Container bên trong scroll
        self.container = QWidget()
        self.grid = QGridLayout(self.container)
        self.grid.setContentsMargins(6, 6, 6, 6)
        self.grid.setHorizontalSpacing(16)
        self.grid.setVerticalSpacing(16)
        self.scroll.setWidget(self.container)

        # Nút Add Node (trải ngang)
        self.add_bar = QPushButton("+ ADD NODE")
        self.add_bar.setObjectName("AddBar")
        self.add_bar.setFixedHeight(44)
        self.add_bar.clicked.connect(self.on_add_node)

        root.addWidget(self.add_bar, 0, Qt.AlignBottom)

        self.rebuild()

    # ---------- Data & UI ----------
    def rebuild(self):
        # Xoá widget cũ
        for i in reversed(range(self.grid.count())):
            w = self.grid.itemAt(i).widget()
            if w:
                w.setParent(None)
                w.deleteLater()

        self.cards.clear()
        nodes = self.store.list()

        # Tạo card
        for n in nodes:
            card = NodeCard(n)
            card.removeRequested.connect(self.on_remove_node)
            card.detailRequested.connect(self.on_detail_node)
            self.cards.append(card)

        self.reflow()

    def reflow(self):
        # Tính columns phù hợp với chiều rộng (có thể nâng cấp tính theo kích thước card)
        w = self.width() if self.width() > 0 else self.parent().width()
        # Heuristic: nếu < 780 px thì 1 cột, ngược lại 2 cột
        self.columns = 1 if w < 780 else 2

        # Đặt cards vào grid
        r = c = 0
        for card in self.cards:
            self.grid.addWidget(card, r, c, Qt.AlignTop)
            c += 1
            if c >= self.columns:
                c = 0
                r += 1

        # Thêm stretch để đẩy các card lên trên
        self.grid.setRowStretch(r + 1, 1)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.reflow()

    # ---------- Actions ----------
    def on_add_node(self):
        dlg = AddNodeDialog(self)
        if dlg.exec_():
            node = dlg.result_node()
            self.store.add(node)
            self.rebuild()

    def on_remove_node(self, node_id: str):
        res = QMessageBox.question(
            self, "Xóa Node", "Bạn có chắc muốn xóa node này?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if res == QMessageBox.Yes:
            self.store.remove(node_id)
            self.rebuild()

    def on_detail_node(self, node_id: str):
        # Bạn có thể mở dialog chi tiết node ở đây
        node = self.store.get(node_id)
        if node:
            QMessageBox.information(self, "Detail",
                                    f"Node ID: {node.id}\nCrops: {node.crops}\nMAC: {node.mac}")