from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QListWidgetItem, QLabel
)
from PyQt5.QtCore import Qt, pyqtSignal


class DiscoveredNode:
    def __init__(
        self,
        uid: str,
        mac: str,
        pumps: int,
        node_type: str = "",
    ):
        self.uid = uid
        self.mac = mac
        self.pumps = pumps
        self.node_type = self._normalize_node_type(node_type)

    def display_text(self):
        return (
            f"{self.uid} | {self.mac} | "
            f"{self.pumps} bơm | {self.node_type or '-'}"
        )

    @staticmethod
    def _normalize_node_type(value: str) -> str:
        v = (value or "").strip().lower()
        if v in ("sensor_node", "sensor", "sensornode"):
            return "sensor_node"
        if v in (
            "pump_node",
            "pump",
            "pumpnode",
            "relay_node",
            "actuator_node",
        ):
            return "pump_node"
        return ""


class DiscoverNodeDialog(QDialog):
    nodeSelected = pyqtSignal(object)

    def __init__(
        self,
        parent=None,
        store=None,
        node_role: str = "Node",
        node_type_filter: str = "",
    ):
        super().__init__(parent)

        self.node_role = (node_role or "Node").strip()
        self.node_type_filter = self._normalize_node_type(node_type_filter)

        self.setWindowTitle(
            self.tr("Quét {role}").format(role=self.node_role)
        )
        self.setModal(True)
        self.resize(420, 360)
        self.store = store
        self._nodes: list[DiscoveredNode] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title = QLabel(
            self.tr("Danh sách {role} khả dụng").format(role=self.node_role)
        )
        layout.addWidget(title)

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget, 1)

        btns = QHBoxLayout()
        self.refresh_btn = QPushButton(self.tr("Làm mới"))
        self.add_btn = QPushButton(self.tr("Thêm"))
        self.close_btn = QPushButton(self.tr("Đóng"))


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
        bus.node_list.connect(self.update_from_snapshot)

    def update_from_snapshot(self, nodes: list):
        self._nodes = nodes
        self.list_widget.clear()

        for n in nodes:
            if not self._matches_type(n):
                continue

            display_name = self._display_name(n)
            text = f"{display_name}  · {n.pumps} bơm"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, n)

            exists = bool(self.store and self.store.has_mac(n.mac))
            item.setData(Qt.UserRole + 1, exists)
            if exists:
                item.setText(item.text() + " (Đã đăng ký)")

            self.list_widget.addItem(item)

        self.add_btn.setEnabled(False)

    # ==================================================
    # ACTIONS
    # ==================================================
    def on_refresh(self):
        self.list_widget.clear()
        self.add_btn.setEnabled(False)
        self.bus.request_node_list()

    def on_add(self):
        item = self.list_widget.currentItem()
        if not item:
            return
        dn = item.data(Qt.UserRole)
        exists = bool(item.data(Qt.UserRole + 1))

        self.nodeSelected.emit(dn)

        if not exists:
            self.bus.send_add_node(dn.mac)

        self.accept()

    def _update_add_state(self):
        self.add_btn.setEnabled(
            self.list_widget.currentItem() is not None
        )

    def _display_name(self, node: DiscoveredNode) -> str:
        name = (getattr(node, "uid", "") or "").strip()
        if (
            not name
            or name.lower() == "esp node"
            or self._looks_like_other_role_name(name)
        ):
            suffix = self._short_mac(getattr(node, "mac", ""))
            return f"{self.node_role} {suffix}".strip()
        return name

    def _looks_like_other_role_name(self, name: str) -> bool:
        lower = (name or "").strip().lower()
        if self.node_type_filter == "pump_node":
            return lower.startswith("sensor")
        if self.node_type_filter == "sensor_node":
            return lower.startswith("pump")
        return False

    def _matches_type(self, node: DiscoveredNode) -> bool:
        if not self.node_type_filter:
            return True
        node_type = self._normalize_node_type(
            getattr(node, "node_type", "")
        )
        if not node_type:
            pumps = int(getattr(node, "pumps", 0) or 0)
            node_type = "pump_node" if pumps > 0 else "sensor_node"
        return node_type == self.node_type_filter

    @staticmethod
    def _normalize_node_type(value: str) -> str:
        v = (value or "").strip().lower()
        if v in ("sensor_node", "sensor", "sensornode"):
            return "sensor_node"
        if v in (
            "pump_node",
            "pump",
            "pumpnode",
            "relay_node",
            "actuator_node",
        ):
            return "pump_node"
        return ""

    @staticmethod
    def _short_mac(mac: str) -> str:
        compact = (mac or "").replace(":", "").replace("-", "")
        compact = compact.upper()
        return compact[-4:] if compact else ""
