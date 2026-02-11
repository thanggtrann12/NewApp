from typing import List
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout,
    QScrollArea, QScroller, QScrollerProperties
)
from widgets.node_card import NodeCard
from models.store import NodeStore


class CardGrid(QWidget):
    """
    - Hiển thị NodeCard theo dạng ROW LIST (1 cột)
    - Vuốt (swipe) thay cho scroll bar
    - Có nút + ADD NODE dưới cùng
    """

    def _setup_smooth_swipe(self):
        # Cấu hình kinetic scrolling
        scroller = QScroller.scroller(self.scroll.viewport())
        props = scroller.scrollerProperties()

        props.setScrollMetric(
            QScrollerProperties.DecelerationFactor, 0.05
        )
        props.setScrollMetric(
            QScrollerProperties.MinimumVelocity, 0.0
        )
        props.setScrollMetric(
            QScrollerProperties.MaximumVelocity, 0.8
        )
        props.setScrollMetric(
            QScrollerProperties.DragStartDistance, 0.001
        )
        props.setScrollMetric(
            QScrollerProperties.FrameRate,
            QScrollerProperties.Fps60
        )

        scroller.setScrollerProperties(props)

        # Grab gesture: cho cả touch + drag chuột trên PC
        QScroller.grabGesture(
            self.scroll.viewport(),
            QScroller.TouchGesture | QScroller.LeftMouseButtonGesture
        )

    def __init__(self, store: NodeStore, bus, crop_registry, parent=None):
        super().__init__(parent)
        self.store = store
        self.bus = bus
        self.crop_registry = crop_registry
        self.cards: List[NodeCard] = []
        self.bus.pump_state.connect(self.on_pump_event)
        # ===== ROOT =====
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        # ===== TITLE =====
        from PyQt5.QtWidgets import QLabel, QPushButton
        title = QLabel(self.tr("IoT Irrigation System"))
        title.setObjectName("AppTitle")
        root.addWidget(title)

        # ===== SCROLL AREA =====
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.NoFrame)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setFocusPolicy(Qt.NoFocus)
        root.addWidget(self.scroll, 1)

        # ===== CONTAINER =====
        self.container = QWidget()
        self.container.setAttribute(Qt.WA_AcceptTouchEvents, True)
        self.list_layout = QVBoxLayout(self.container)
        self.list_layout.setContentsMargins(6, 6, 6, 6)
        self.list_layout.setSpacing(16)
        self.scroll.setWidget(self.container)

        # ===== ENABLE SWIPE =====
        self._setup_smooth_swipe()

        # ===== ADD NODE BUTTON =====
        self.add_bar = QPushButton(self.tr("+ ADD NODE"))
        self.add_bar.setObjectName("AddBar")
        self.add_bar.setFixedHeight(64)
        self.add_bar.clicked.connect(self.on_add_node)
        root.addWidget(self.add_bar)

        self.rebuild()

    # ======================================================
    # BUILD UI FROM STORE
    # ======================================================
    def rebuild(self):
        while self.list_layout.count():
            w = self.list_layout.takeAt(0).widget()
            if w:
                w.deleteLater()

        self.cards.clear()

        for node in self.store.list():
            card = NodeCard(node, self.crop_registry, self.bus)
            card.configChanged.connect(self.on_node_config_changed)
            card.removeRequested.connect(self.on_remove_node)
            card.detailRequested.connect(self.on_detail_node)

            self.cards.append(card)
            self.list_layout.addWidget(card)
            card._build_pump_list()

        self.list_layout.addStretch(1)

    # ======================================================
    # ACTIONS
    # ======================================================
    def on_add_node(self):
        from dialogs.discover_node_dialog import DiscoverNodeDialog, DiscoveredNode

        dlg = DiscoverNodeDialog(self, self.store)

        def on_selected(dn: DiscoveredNode):
            from models.node import Node
            node = Node.new(name=dn.uid)
            node.mac = dn.mac
            node.pumps = dn.pumps
            self.store.add_or_update_by_mac(node)
            self.rebuild()

        dlg.nodeSelected.connect(on_selected)
        dlg.bind_bus(self.bus)
        self.bus.get_node_list()
        dlg.exec_()

    def on_remove_node(self, node_id: str):
        from PyQt5.QtWidgets import QMessageBox
        res = QMessageBox.question(
            self,
            self.tr("Remove Node"),
            self.tr("Are you sure you want to remove this node?"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if res != QMessageBox.Yes:
            return
        self.store.remove(node_id)
        self.rebuild()

    def on_detail_node(self, node_id: str):
        node = self.store.get(node_id)
        if not node:
            return
        from dialogs.node_detail_dialog import NodeDetailDialog
        dlg = NodeDetailDialog(node, self.crop_registry, self)
        if dlg.exec_():
            self.store.save()
            self.rebuild()

    def on_pump_command(self, node_id: str, pump_idx: int, cmd: str):
        print(f"[UI → BUS] Node={node_id} Pump={pump_idx+1} CMD={cmd}")
        self.bus.send_manual(node_id, pump_idx, cmd)

    def on_node_config_changed(self, node_id: str):
        print(f"[STORE] save config node={node_id}")
        self.store.save()

    def on_pump_event(self, evt):
        for card in self.cards:
            if card.node.id == evt.node_id:
                card.update_from_device(
                    evt.pump_idx,
                    evt.state,
                    evt.next_schedule
                )