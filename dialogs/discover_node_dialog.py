from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QListWidgetItem, QLabel
)
from PyQt5.QtCore import Qt, pyqtSignal


class DiscoveredNode:
    def __init__(self, uid: str, mac: str, pumps: int):
        self.uid = uid
        self.mac = mac
        self.pumps = pumps

    def display_text(self):
        return f"{self.uid} | {self.mac} | {self.pumps} Pumps"


class DiscoverNodeDialog(QDialog):
    nodeSelected = pyqtSignal(object)   # DiscoveredNode

    def __init__(self, parent=None, store=None):
        super().__init__(parent)

        self.setWindowTitle("Discover Nodes")
        self.setModal(True)
        self.resize(420, 360)
        self.store = store
        self._nodes: list[DiscoveredNode] = []

        # ===== UI =====
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title = QLabel("Available Nodes")
        layout.addWidget(title)

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget, 1)

        btns = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh")
        self.add_btn = QPushButton("Add")
        self.close_btn = QPushButton("Close")

        for b in (self.refresh_btn, self.add_btn, self.close_btn):
            b.setMinimumHeight(52)

        self.add_btn.setEnabled(False)

        btns.addWidget(self.refresh_btn)
        btns.addStretch(1)
        btns.addWidget(self.add_btn)
        btns.addWidget(self.close_btn)
        layout.addLayout(btns)

        # ===== SIGNALS =====
        self.refresh_btn.clicked.connect(self.on_refresh)
        self.close_btn.clicked.connect(self.reject)
        self.add_btn.clicked.connect(self.on_add)
        self.list_widget.itemSelectionChanged.connect(
            self._update_add_state
        )
    # ==================================================
    # BUS BINDING (SNAPSHOT)
    # ==================================================
    def bind_bus(self, bus):
        self.bus = bus
        bus.nodeSnapshot.connect(self.update_from_snapshot)

    def update_from_snapshot(self, nodes: list):
        self._nodes = nodes
        self.list_widget.clear()

        for n in nodes:
            item = QListWidgetItem(n.display_text())
            if self.store.has_mac(n.mac):
                print(f"[DISCOVER] skipping existing node {n.mac}")
                item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
                item.setText(item.text() + " (Added)")
            else:
                item.setData(Qt.UserRole, n)
            self.list_widget.addItem(item)

        self.add_btn.setEnabled(False)

    # ==================================================
    # ACTIONS
    # ==================================================
    def on_refresh(self):
        self.list_widget.clear()
        self.add_btn.setEnabled(False)
        self.bus.get_node_list()

    def on_add(self):
        item = self.list_widget.currentItem()
        if not item:
            return
        self.nodeSelected.emit(item.data(Qt.UserRole))
        self.bus.send_add_node(item.data(Qt.UserRole).mac)
        self.accept()

    def _update_add_state(self):
        self.add_btn.setEnabled(
            self.list_widget.currentItem() is not None
        )
