from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from models.zone import Zone


class AddZoneDialog(QDialog):
    def __init__(self, node_store, bus, crop_registry, parent=None):
        super().__init__(parent)
        self.node_store = node_store
        self.bus = bus
        self.crop_registry = crop_registry

        self.setWindowTitle(self.tr("Thêm khu tưới"))
        self.setModal(True)
        self.resize(700, 520)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        info_box = QGroupBox(self.tr("Thông tin khu tưới"))
        info_layout = QVBoxLayout(info_box)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText(
            self.tr("Tên khu tưới (ví dụ: Khu 1)")
        )

        info_layout.addWidget(QLabel(self.tr("Tên:")))
        info_layout.addWidget(self.name_edit)
        layout.addWidget(info_box)

        mapping_box = QGroupBox(self.tr("Gán thiết bị"))
        mapping_layout = QVBoxLayout(mapping_box)

        sensor_node_row = QHBoxLayout()
        sensor_node_row.addWidget(QLabel(self.tr("Cảm biến:")))
        self.sensor_node_combo = QComboBox()
        sensor_node_row.addWidget(self.sensor_node_combo, 1)

        self.add_sensor_node_btn = QPushButton(self.tr("Thêm node cảm biến"))
        self.add_sensor_node_btn.clicked.connect(self._on_add_sensor_node)
        sensor_node_row.addWidget(self.add_sensor_node_btn)
        mapping_layout.addLayout(sensor_node_row)

        sensor_note = QLabel(self.tr("Mỗi địa chỉ MAC cảm biến là một cụm cảm biến."))
        sensor_note.setObjectName("SensorLabel")
        sensor_note.setWordWrap(True)
        mapping_layout.addWidget(sensor_note)

        pump_node_row = QHBoxLayout()
        pump_node_row.addWidget(QLabel(self.tr("Bơm:")))
        self.pump_node_combo = QComboBox()
        pump_node_row.addWidget(self.pump_node_combo, 1)

        self.add_pump_node_btn = QPushButton(self.tr("Thêm node bơm"))
        self.add_pump_node_btn.clicked.connect(self._on_add_pump_node)
        pump_node_row.addWidget(self.add_pump_node_btn)
        mapping_layout.addLayout(pump_node_row)

        pump_row = QHBoxLayout()
        pump_row.addWidget(QLabel(self.tr("Bơm:")))
        self.pump_combo = QComboBox()
        pump_row.addWidget(self.pump_combo, 1)
        mapping_layout.addLayout(pump_row)

        crop_row = QHBoxLayout()
        crop_row.addWidget(QLabel(self.tr("Cây trồng:")))
        self.crop_lbl = QLabel(self.tr("Chưa đặt"))
        self.crop_lbl.setObjectName("SensorLabel")
        crop_row.addWidget(self.crop_lbl, 1)

        self.select_crop_btn = QPushButton(self.tr("Chọn cây"))
        self.select_crop_btn.clicked.connect(self._select_crop)
        crop_row.addWidget(self.select_crop_btn)
        mapping_layout.addLayout(crop_row)

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel(self.tr("Chế độ:")))
        self.mode_lbl = QLabel("-")
        self.mode_lbl.setObjectName("SensorLabel")
        mode_row.addWidget(self.mode_lbl, 1)

        self.config_mode_btn = QPushButton(self.tr("Cấu hình Lịch/Hẹn giờ"))
        self.config_mode_btn.clicked.connect(self._open_mode_config)
        mode_row.addWidget(self.config_mode_btn)
        mapping_layout.addLayout(mode_row)

        help_lbl = QLabel(
            self.tr(
                "Mẹo: Dùng nút thêm node nếu thiết bị chưa có trong danh sách."
            )
        )
        help_lbl.setObjectName("SensorLabel")
        help_lbl.setWordWrap(True)
        mapping_layout.addWidget(help_lbl)

        layout.addWidget(mapping_box, 1)

        self.pump_node_combo.currentIndexChanged.connect(
            self._on_pump_node_changed
        )
        self.pump_combo.currentIndexChanged.connect(
            self._refresh_irrigation_preview
        )

        self._reload_node_combos()

        btns = QHBoxLayout()
        btns.addStretch(1)

        cancel = QPushButton(self.tr("Đóng"))
        ok = QPushButton(self.tr("Thêm"))
        ok.setObjectName("DetailButton")
        ok.setMinimumHeight(40)
        ok.setDefault(True)

        cancel.clicked.connect(self.reject)
        ok.clicked.connect(self.accept)

        btns.addWidget(cancel)
        btns.addWidget(ok)
        layout.addLayout(btns)

    def result_zone(self, default_name: str = "Khu") -> Zone:
        name = self.name_edit.text().strip() or default_name
        zone = Zone.new(name=name)

        zone.sensor_node_id = self.sensor_node_combo.currentData() or ""
        zone.pump_node_id = self.pump_node_combo.currentData() or ""
        zone.sensor_indices = []

        raw_pump_idx = self.pump_combo.currentData()
        zone.pump_idx = (
            int(raw_pump_idx)
            if isinstance(raw_pump_idx, int)
            else None
        )

        return zone

    def _display_node_name(
        self,
        node,
        role_label: str,
        expected_type: str,
    ) -> str:
        name = (getattr(node, "name", "") or "").strip()
        if (
            not name
            or self._is_generic_name(name)
            or self._looks_like_other_role_name(name, expected_type)
        ):
            mac_suffix = self._short_mac(getattr(node, "mac", ""))
            return f"{role_label} {mac_suffix}".strip()
        return name

    def _sensor_node_label(self, node) -> str:
        return self._display_node_name(
            node,
            self.tr("Cảm biến"),
            "sensor_node",
        )

    def _pump_node_label(self, node) -> str:
        return self._display_node_name(
            node,
            self.tr("Bơm"),
            "pump_node",
        )

    @staticmethod
    def _is_generic_name(name: str) -> bool:
        return (name or "").strip().lower() == "esp node"

    @staticmethod
    def _short_mac(mac: str) -> str:
        compact = (mac or "").replace(":", "").replace("-", "").upper()
        return compact[-4:] if compact else ""

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
    def _looks_like_other_role_name(name: str, expected_type: str) -> bool:
        lower = (name or "").strip().lower()
        role = (expected_type or "").strip().lower()
        if role == "pump_node":
            return lower.startswith("sensor")
        if role == "sensor_node":
            return lower.startswith("pump")
        return False

    def _matches_node_type(self, node, expected_type: str) -> bool:
        node_type = self._normalize_node_type(
            getattr(node, "node_type", "")
        )
        if not node_type:
            pumps = int(getattr(node, "pumps", 0) or 0)
            node_type = "pump_node" if pumps > 0 else "sensor_node"
        return node_type == expected_type

    def _reload_node_combos(
        self,
        select_sensor_node_id: str = "",
        select_pump_node_id: str = "",
    ):
        current_sensor = select_sensor_node_id or (
            self.sensor_node_combo.currentData() or ""
        )
        current_pump = select_pump_node_id or (
            self.pump_node_combo.currentData() or ""
        )

        self.sensor_node_combo.blockSignals(True)
        self.pump_node_combo.blockSignals(True)

        self.sensor_node_combo.clear()
        self.pump_node_combo.clear()

        self.sensor_node_combo.addItem(self.tr("Chưa đặt"), "")
        self.pump_node_combo.addItem(self.tr("Chưa đặt"), "")

        for node in self.node_store.list():
            if self._matches_node_type(node, "sensor_node") or node.id == current_sensor:
                self.sensor_node_combo.addItem(
                    self._sensor_node_label(node),
                    node.id,
                )

            if self._matches_node_type(node, "pump_node") or node.id == current_pump:
                self.pump_node_combo.addItem(
                    self._pump_node_label(node),
                    node.id,
                )

        sensor_idx = self.sensor_node_combo.findData(current_sensor)
        self.sensor_node_combo.setCurrentIndex(sensor_idx if sensor_idx >= 0 else 0)

        pump_idx = self.pump_node_combo.findData(current_pump)
        self.pump_node_combo.setCurrentIndex(pump_idx if pump_idx >= 0 else 0)

        self.sensor_node_combo.blockSignals(False)
        self.pump_node_combo.blockSignals(False)

        self._on_pump_node_changed()

    def _current_pump_node(self):
        node_id = self.pump_node_combo.currentData()
        if not node_id:
            return None
        return self.node_store.get(node_id)

    def _on_pump_node_changed(self):
        node = self._current_pump_node()
        self.pump_combo.clear()
        self.pump_combo.addItem(self.tr("Chưa đặt"), None)

        if not node or int(getattr(node, "pumps", 0)) <= 0:
            self._refresh_irrigation_preview()
            return

        for idx in range(node.pumps):
            self.pump_combo.addItem(
                self.tr("Bơm {n}").format(n=idx + 1),
                idx,
            )

        self._refresh_irrigation_preview()

    def _active_pump_target(self):
        node = self._current_pump_node()
        pump_idx = self.pump_combo.currentData()
        if not node or not isinstance(pump_idx, int):
            return None, None

        node.pump_crop_map = getattr(node, "pump_crop_map", {})
        node.pump_mode = getattr(node, "pump_mode", {})
        node.auto_type = getattr(node, "auto_type", {})
        node.pump_schedule = getattr(node, "pump_schedule", {})
        return node, pump_idx

    def _refresh_irrigation_preview(self):
        node, pump_idx = self._active_pump_target()
        enabled = node is not None and pump_idx is not None

        self.select_crop_btn.setEnabled(enabled)
        self.config_mode_btn.setEnabled(enabled)

        if not enabled:
            self.crop_lbl.setText(self.tr("Chưa đặt"))
            self.mode_lbl.setText("-")
            return

        crop_id = node.pump_crop_map.get(pump_idx)
        crop = self.crop_registry.get(crop_id) if crop_id else None
        self.crop_lbl.setText(crop.name if crop else self.tr("Chưa đặt"))

        auto_type = self._normalize_auto_type(
            node.auto_type.get(pump_idx, "SCHEDULE")
        )
        self.mode_lbl.setText(self._auto_type_label(auto_type))

    def _select_crop(self):
        node, pump_idx = self._active_pump_target()
        if not node:
            return

        from dialogs.crop_select_dialog import CropSelectDialog

        dlg = CropSelectDialog(self.crop_registry, self)
        if not dlg.exec_() or not dlg.selected_crop:
            return

        node.pump_crop_map[pump_idx] = dlg.selected_crop.id
        self.node_store.save()
        self._emit_config_changed(node.id)
        self._refresh_irrigation_preview()

    def _open_mode_config(self):
        node, pump_idx = self._active_pump_target()
        if not node:
            return

        from dialogs.pump_control_dialog import PumpControlDialog

        dlg = PumpControlDialog(node, pump_idx, self.crop_registry, self)
        if not dlg.exec_():
            return

        data = dlg.result_data()
        node.pump_mode[pump_idx] = data["mode"]
        node.auto_type[pump_idx] = data["auto_type"]
        node.pump_schedule[pump_idx] = data["schedule"]
        self.node_store.save()
        self._emit_config_changed(node.id)
        self._refresh_irrigation_preview()

    @staticmethod
    def _normalize_auto_type(value: str) -> str:
        if value == "RECOMMEND":
            return "SCHEDULE"
        if value in ("SCHEDULE", "TIMER"):
            return value
        return "SCHEDULE"

    @staticmethod
    def _auto_type_label(auto_type: str) -> str:
        if auto_type == "TIMER":
            return "HẸN GIỜ"
        return "LỊCH"

    def _discover_node(self, node_role: str, node_type: str) -> str:
        from dialogs.discover_node_dialog import DiscoverNodeDialog, DiscoveredNode
        from models.node import Node

        dlg = DiscoverNodeDialog(
            self,
            self.node_store,
            node_role=node_role,
            node_type_filter=node_type,
        )
        selected_node_id = ""

        def on_selected(dn: DiscoveredNode):
            nonlocal selected_node_id
            existing = self.node_store.get_by_mac(dn.mac)
            if existing:
                changed = False
                if int(dn.pumps or 0) > 0 and existing.pumps != int(dn.pumps):
                    existing.pumps = int(dn.pumps)

                    changed = True

                discovered_type = (
                    self._normalize_node_type(getattr(dn, "node_type", ""))
                    or self._normalize_node_type(node_type)
                )
                if discovered_type and self._normalize_node_type(existing.node_type) != discovered_type:
                    existing.node_type = discovered_type
                    changed = True

                if changed:
                    self.node_store.save()
                    self._emit_config_changed(existing.id)

                selected_node_id = existing.id
                return

            serial_name = (dn.uid or "").strip()
            if (
                not serial_name
                or self._is_generic_name(serial_name)
                or self._looks_like_other_role_name(
                    serial_name,
                    node_type,
                )
            ):
                serial_name = f"{node_role} {self._short_mac(dn.mac)}".strip()

            node = Node.new(name=serial_name)
            node.mac = dn.mac
            node.pumps = dn.pumps
            node.node_type = (
                self._normalize_node_type(getattr(dn, "node_type", ""))
                or self._normalize_node_type(node_type)
            )
            selected = self.node_store.add_or_update_by_mac(node)
            selected_node_id = selected.id
            self._emit_config_changed(selected.id)

        dlg.nodeSelected.connect(on_selected)
        dlg.bind_bus(self.bus)
        self.bus.request_node_list()
        dlg.exec_()

        return selected_node_id

    def _on_add_sensor_node(self):
        selected_node_id = self._discover_node(
            self.tr("Cảm biến"),
            "sensor_node",
        )
        if selected_node_id:
            self._reload_node_combos(select_sensor_node_id=selected_node_id)

    def _on_add_pump_node(self):
        selected_node_id = self._discover_node(
            self.tr("Bơm"),
            "pump_node",
        )
        if selected_node_id:
            self._reload_node_combos(select_pump_node_id=selected_node_id)

    def _emit_config_changed(self, node_id: str):
        if not self.bus or not node_id:
            return
        if hasattr(self.bus, "notify_config_changed"):
            self.bus.notify_config_changed(node_id)
            return
        if hasattr(self.bus, "config_changed"):
            self.bus.config_changed.emit(node_id)
