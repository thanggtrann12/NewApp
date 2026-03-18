from typing import List

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QMessageBox,
    QScrollArea,
    QScroller,
    QScrollerProperties,
    QVBoxLayout,
    QWidget,
)

from dialogs.add_zone_dialog import AddZoneDialog
from dialogs.zone_detail_dialog import ZoneDetailDialog
from widgets.zone_card import ZoneCard


class ZoneGrid(QWidget):
    def _setup_smooth_swipe(self):
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
            QScrollerProperties.Fps60,
        )

        scroller.setScrollerProperties(props)

        QScroller.grabGesture(
            self.scroll.viewport(),
            QScroller.TouchGesture | QScroller.LeftMouseButtonGesture,
        )

    def __init__(
        self,
        zone_store,
        node_store,
        bus,
        crop_registry,
        parent=None,
    ):
        super().__init__(parent)
        self.zone_store = zone_store
        self.node_store = node_store
        self.bus = bus
        self.crop_registry = crop_registry
        self.cards: List[ZoneCard] = []

        self.bus.sensor_data.connect(self.on_sensor_event)
        self.bus.pump_state.connect(self.on_pump_event)
        self.bus.node_list.connect(self.on_node_list)
        self.bus.zones_changed.connect(self.on_zones_changed)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        from PyQt5.QtWidgets import QLabel, QPushButton

        title = QLabel(self.tr("Hệ thống tưới thông minh"))
        title.setObjectName("AppTitle")
        root.addWidget(title)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("ZoneScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.NoFrame)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setFocusPolicy(Qt.NoFocus)
        root.addWidget(self.scroll, 1)

        self.container = QWidget()
        self.container.setObjectName("ZoneList")
        self.container.setAttribute(Qt.WA_AcceptTouchEvents, True)
        self.list_layout = QVBoxLayout(self.container)
        self.list_layout.setContentsMargins(6, 6, 6, 6)
        self.list_layout.setSpacing(16)
        self.scroll.setWidget(self.container)

        self._setup_smooth_swipe()

        self.add_bar = QPushButton(self.tr("THÊM KHU TƯỚI"))
        self.add_bar.setObjectName("AddBar")
        self.add_bar.setProperty("variant", "accent")
        self.add_bar.setFixedHeight(64)
        self.add_bar.clicked.connect(self.on_add_zone)
        root.addWidget(self.add_bar)

        self.rebuild()

    def rebuild(self):
        while self.list_layout.count():
            widget = self.list_layout.takeAt(0).widget()
            if widget:
                widget.deleteLater()

        self.cards.clear()

        for zone in self.zone_store.list():
            card = ZoneCard(
                zone,
                self.node_store,
                self.crop_registry,
                self.bus,
            )
            card.removeRequested.connect(self.on_remove_zone)
            card.detailRequested.connect(self.on_detail_zone)

            self.cards.append(card)
            self.list_layout.addWidget(card)

        self.list_layout.addStretch(1)

    def on_add_zone(self):
        dlg = AddZoneDialog(
            self.node_store,
            self.bus,
            self.crop_registry,
            self,
        )
        if not dlg.exec_():
            return

        default_name = self.tr("Khu {n}").format(
            n=len(self.zone_store.list()) + 1
        )
        zone = dlg.result_zone(default_name=default_name)

        self.zone_store.add(zone)
        self._notify_zones_changed()

    def on_remove_zone(self, zone_id: str):
        res = QMessageBox.question(
            self,
            self.tr("Xóa khu tưới"),
            self.tr("Bạn có chắc muốn xóa khu tưới này không?"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if res != QMessageBox.Yes:
            return

        self.zone_store.remove(zone_id)
        self._notify_zones_changed()

    def on_detail_zone(self, zone_id: str):
        zone = self.zone_store.get(zone_id)
        if not zone:
            return

        dlg = ZoneDetailDialog(
            zone,
            self.node_store,
            self.crop_registry,
            self.bus,
            self,
        )
        if dlg.exec_():
            if getattr(dlg, "remove_requested", False):
                self.zone_store.remove(zone_id)
                self._notify_zones_changed()
                return
            self.zone_store.save()
            self._notify_zones_changed()

    def on_sensor_event(self, evt):
        for card in self.cards:
            card.on_sensor_event(evt)

    def on_pump_event(self, evt):
        for card in self.cards:
            card.on_pump_event(evt)

    def on_node_list(self, _nodes):
        for card in self.cards:
            card.refresh()

    def on_zones_changed(self):
        self.rebuild()

    def _notify_zones_changed(self):
        if not self.bus:
            return
        if hasattr(self.bus, "notify_zones_changed"):
            self.bus.notify_zones_changed()
            return
        if hasattr(self.bus, "zones_changed"):
            self.bus.zones_changed.emit()
