from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class ZoneCard(QFrame):
    removeRequested = pyqtSignal(str)
    detailRequested = pyqtSignal(str)
    DRY_THRESHOLD = 35.0

    def __init__(self, zone, node_store, crop_registry, bus=None, parent=None):
        super().__init__(parent)
        self.zone = zone
        self.node_store = node_store
        self.crop_registry = crop_registry
        self.bus = bus

        self.setObjectName("Card")
        self.setMinimumWidth(320)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(8)
        shadow.setColor(QColor(0, 0, 0, 120))
        shadow.setOffset(0, 3)
        self.setGraphicsEffect(shadow)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(8)

        header = QHBoxLayout()

        self.title_lbl = QLabel(self.zone.name or self.tr("Khu tưới"))
        self.title_lbl.setObjectName("CardTitle")

        close_btn = QPushButton("×")
        close_btn.setObjectName("CloseButton")
        close_btn.setFixedSize(34, 28)
        close_btn.clicked.connect(
            lambda: self.removeRequested.emit(self.zone.id)
        )

        header.addWidget(self.title_lbl, 1)
        header.addWidget(close_btn)

        self.crop_sub_lbl = QLabel()
        self.crop_sub_lbl.setObjectName("ZoneCropSub")

        # ===== SETUP REQUIRED STATE =====
        self.setup_wrap = QWidget()
        setup_layout = QVBoxLayout(self.setup_wrap)
        setup_layout.setContentsMargins(0, 0, 0, 0)
        setup_layout.setSpacing(6)

        self.setup_title_lbl = QLabel(self.tr("Cần thiết lập"))
        self.setup_title_lbl.setObjectName("ZoneSetupTitle")
        setup_layout.addWidget(self.setup_title_lbl)

        sensor_setup_row = QHBoxLayout()
        sensor_setup_row.setContentsMargins(0, 0, 0, 0)
        sensor_setup_row.setSpacing(8)
        sensor_setup_row.addWidget(QLabel(self.tr("Cảm biến:")))
        self.setup_sensor_btn = QPushButton(self.tr("Chọn"))
        self.setup_sensor_btn.setObjectName("ZoneInlineButton")
        self.setup_sensor_btn.setProperty("variant", "ghost")
        self.setup_sensor_btn.clicked.connect(
            lambda: self.detailRequested.emit(self.zone.id)
        )
        sensor_setup_row.addWidget(self.setup_sensor_btn)
        sensor_setup_row.addStretch(1)
        setup_layout.addLayout(sensor_setup_row)

        pump_setup_row = QHBoxLayout()
        pump_setup_row.setContentsMargins(0, 0, 0, 0)
        pump_setup_row.setSpacing(8)
        pump_setup_row.addWidget(QLabel(self.tr("Bơm:")))
        self.setup_pump_btn = QPushButton(self.tr("Chọn"))
        self.setup_pump_btn.setObjectName("ZoneInlineButton")
        self.setup_pump_btn.setProperty("variant", "ghost")
        self.setup_pump_btn.clicked.connect(
            lambda: self.detailRequested.emit(self.zone.id)
        )
        pump_setup_row.addWidget(self.setup_pump_btn)
        pump_setup_row.addStretch(1)
        setup_layout.addLayout(pump_setup_row)

        crop_setup_row = QHBoxLayout()
        crop_setup_row.setContentsMargins(0, 0, 0, 0)
        crop_setup_row.setSpacing(8)
        crop_setup_row.addWidget(QLabel(self.tr("Loại cây:")))
        self.setup_crop_btn = QPushButton(self.tr("Chọn"))
        self.setup_crop_btn.setObjectName("ZoneInlineButton")
        self.setup_crop_btn.setProperty("variant", "ghost")
        self.setup_crop_btn.clicked.connect(
            lambda: self.detailRequested.emit(self.zone.id)
        )
        crop_setup_row.addWidget(self.setup_crop_btn)
        crop_setup_row.addStretch(1)
        setup_layout.addLayout(crop_setup_row)

        self.create_zone_btn = QPushButton(self.tr("Thiết lập khu"))
        self.create_zone_btn.setObjectName("ZoneInlineButton")
        self.create_zone_btn.setProperty("variant", "accent")
        self.create_zone_btn.clicked.connect(
            lambda: self.detailRequested.emit(self.zone.id)
        )
        setup_layout.addWidget(self.create_zone_btn)

        # ===== CONFIGURED STATE =====
        self.content_wrap = QWidget()
        content_layout = QVBoxLayout(self.content_wrap)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(8)

        self.sensors_lbl = QLabel()
        self.sensors_lbl.setWordWrap(True)
        self.sensors_lbl.setObjectName("ZoneMeta")

        self.pump_lbl = QLabel()
        self.pump_lbl.setWordWrap(True)
        self.pump_lbl.setObjectName("ZoneMeta")

        self.metrics_wrap = QWidget()
        self.metrics_wrap.setObjectName("ZoneMetricsPanel")
        metrics_layout = QGridLayout(self.metrics_wrap)
        metrics_layout.setContentsMargins(0, 0, 0, 0)
        metrics_layout.setHorizontalSpacing(24)
        metrics_layout.setVerticalSpacing(4)

        self.moisture_name_lbl = QLabel(self.tr("Độ ẩm đất"))
        self.moisture_name_lbl.setObjectName("ZoneMetricName")
        self.moisture_value_lbl = QLabel("-")
        self.moisture_value_lbl.setObjectName("ZoneMetricValue")

        self.temp_name_lbl = QLabel(self.tr("Nhiệt độ"))
        self.temp_name_lbl.setObjectName("ZoneMetricName")
        self.temp_value_lbl = QLabel("-")
        self.temp_value_lbl.setObjectName("ZoneMetricValue")

        self.humi_name_lbl = QLabel(self.tr("Độ ẩm không khí"))
        self.humi_name_lbl.setObjectName("ZoneMetricName")
        self.humi_value_lbl = QLabel("-")
        self.humi_value_lbl.setObjectName("ZoneMetricValue")

        metrics_layout.addWidget(self.moisture_name_lbl, 0, 0)
        metrics_layout.addWidget(self.temp_name_lbl, 0, 1)
        metrics_layout.addWidget(self.moisture_value_lbl, 1, 0)
        metrics_layout.addWidget(self.temp_value_lbl, 1, 1)
        metrics_layout.addWidget(self.humi_name_lbl, 0, 2)
        metrics_layout.addWidget(self.humi_value_lbl, 1, 2)

        self.status_lbl = QLabel(self.tr("Chế độ: -"))
        self.status_lbl.setObjectName("ZoneStatus")
        self.status_lbl.setProperty("kind", "na")
        self.status_lbl.setWordWrap(True)

        self.reason_lbl = QLabel("")
        self.reason_lbl.setObjectName("ZoneReason")
        self.reason_lbl.setWordWrap(True)

        self.actions_wrap = QWidget()
        self.actions_wrap.setObjectName("ZoneActions")
        actions_layout = QHBoxLayout(self.actions_wrap)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(10)

        self.detail_btn = QPushButton(self.tr("Chi tiết"))
        self.detail_btn.setObjectName("ZoneInlineButton")
        self.detail_btn.setProperty("variant", "ghost")
        self.detail_btn.clicked.connect(
            lambda: self.detailRequested.emit(self.zone.id)
        )

        self.test_btn = QPushButton(self.tr("Bật bơm"))
        self.test_btn.setObjectName("ZoneInlineButton")
        self.test_btn.setProperty("variant", "accent")
        self.test_btn.clicked.connect(self._on_test_water)

        actions_layout.addWidget(self.detail_btn)
        actions_layout.addWidget(self.test_btn)
        actions_layout.addStretch(1)

        content_layout.addWidget(self.metrics_wrap)
        content_layout.addWidget(self.status_lbl)
        content_layout.addWidget(self.reason_lbl)
        content_layout.addWidget(self.pump_lbl)
        content_layout.addWidget(self.sensors_lbl)
        content_layout.addWidget(self.actions_wrap)

        root.addLayout(header)
        root.addWidget(self.crop_sub_lbl)
        root.addWidget(self.setup_wrap)
        root.addWidget(self.content_wrap)

        self.refresh()

    def refresh(self):
        title = self.zone.name or self.tr("Khu mới")
        self.title_lbl.setText(f"🌱  {title}")

        crop_text = self._crop_text()
        self.crop_sub_lbl.setText(crop_text if crop_text != self.tr("Chưa đặt") else "")

        self._refresh_identity_labels()
        setup_required = self._is_setup_required()
        self.setup_wrap.setVisible(setup_required)
        self.content_wrap.setVisible(not setup_required)

        self._refresh_setup_controls()
        self._update_metrics_and_status()
        self._refresh_test_button()

    def on_sensor_event(self, evt):
        if evt.node_id != self.zone.sensor_node_id:
            return

        self.zone.sensor_cache = dict(evt.readings or {})
        self._refresh_identity_labels()
        self._update_metrics_and_status()

    def on_pump_event(self, evt):
        node, pump_idx = self._active_pump_target()
        if not node or pump_idx is None:
            return
        if evt.node_id != node.id or evt.pump_idx != pump_idx:
            return

        node.pump_state = getattr(node, "pump_state", {})
        node.pump_state[pump_idx] = evt.state
        self._refresh_identity_labels()
        self._update_metrics_and_status()
        self._refresh_test_button()

    def _refresh_identity_labels(self):
        self.sensors_lbl.setText(
            self.tr("Cảm biến: {node}").format(node=self._sensor_node_text())
        )
        self.pump_lbl.setText(
            self.tr("Bơm: {text}").format(text=self._pump_compact_text())
        )

    def _pump_text(self) -> str:
        node, pump_idx = self._active_pump_target()
        if not node or pump_idx is None:
            return self.tr("Chưa đặt")

        node_name = node.name or self.tr("Node ESP")
        return self.tr("{node} / Bơm {n}").format(
            node=node_name,
            n=pump_idx + 1,
        )

    def _crop_text(self) -> str:
        node, pump_idx = self._active_pump_target()
        if not node or pump_idx is None:
            return self.tr("Chưa đặt")

        crop_id = getattr(node, "pump_crop_map", {}).get(pump_idx)
        crop = self.crop_registry.get(crop_id) if crop_id else None
        return crop.name if crop else self.tr("Chưa đặt")

    def _mode_text(self) -> str:
        node, pump_idx = self._active_pump_target()
        if not node or pump_idx is None:
            return self.tr("Chế độ: -")

        auto_type = self._normalize_auto_type(
            getattr(node, "auto_type", {}).get(pump_idx, "SCHEDULE")
        )
        return self.tr("Chế độ: {auto}").format(
            auto=self._auto_type_label(auto_type)
        )

    def _sensor_node_text(self) -> str:
        if not self.zone.sensor_node_id:
            return self.tr("Chưa đặt")

        node = self.node_store.get(self.zone.sensor_node_id)
        if not node:
            return self.tr("Chưa đặt")

        return node.name or self.tr("Node ESP")

    def _active_pump_target(self):
        if self.zone.pump_idx is None or not self.zone.pump_node_id:
            return None, None

        node = self.node_store.get(self.zone.pump_node_id)
        if not node:
            return None, None

        return node, self.zone.pump_idx

    def _pump_compact_text(self) -> str:
        node, pump_idx = self._active_pump_target()
        if not node or pump_idx is None:
            return self.tr("Chưa đặt")
        return self.tr("Bơm-{n}").format(n=f"{pump_idx + 1:02d}")

    def _is_setup_required(self) -> bool:
        node, pump_idx = self._active_pump_target()
        if not self.zone.sensor_node_id or not node or pump_idx is None:
            return True

        crop_id = getattr(node, "pump_crop_map", {}).get(pump_idx)
        return not bool(crop_id)

    def _refresh_setup_controls(self):
        sensor_name = self._sensor_node_text()
        pump_name = self._pump_compact_text()
        crop_name = self._crop_text()

        self.setup_sensor_btn.setText(
            sensor_name if sensor_name != self.tr("Chưa đặt") else self.tr("Chọn")
        )
        self.setup_pump_btn.setText(
            pump_name if pump_name != self.tr("Chưa đặt") else self.tr("Chọn")
        )
        self.setup_crop_btn.setText(
            crop_name if crop_name != self.tr("Chưa đặt") else self.tr("Chọn")
        )

    def _update_metrics_and_status(self):
        readings = self.zone.sensor_cache if isinstance(self.zone.sensor_cache, dict) else {}

        moisture = self._as_float(readings.get("moisture"))
        temperature = self._as_float(
            readings.get("temperature", readings.get("temp"))
        )
        humidity = self._as_float(
            readings.get("humidity", readings.get("humi"))
        )

        moisture_txt = (
            f"{int(round(moisture))}%" if moisture is not None else "-"
        )
        temperature_txt = (
            f"{temperature:.1f}°C" if temperature is not None else "-"
        )
        humidity_txt = (
            f"{int(round(humidity))}%" if humidity is not None else "-"
        )

        self.moisture_value_lbl.setText(moisture_txt)
        self.temp_value_lbl.setText(temperature_txt)
        self.humi_value_lbl.setText(humidity_txt)

        status_text, status_kind, reason_text = self._automation_status_text()

        self.status_lbl.setProperty("kind", status_kind)
        self.status_lbl.style().unpolish(self.status_lbl)
        self.status_lbl.style().polish(self.status_lbl)
        self.status_lbl.setText(status_text)

        self.reason_lbl.setText(reason_text)
        self.reason_lbl.setVisible(bool(reason_text))

    def _automation_status_text(self):
        node, pump_idx = self._active_pump_target()
        if not node or pump_idx is None:
            return self.tr("Chế độ: -"), "na", ""

        auto_type = self._normalize_auto_type(
            getattr(node, "auto_type", {}).get(pump_idx, "SCHEDULE")
        )
        pump_state = getattr(node, "pump_state", {}).get(pump_idx, "OFF")
        state_txt = "BẬT" if pump_state == "ON" else "TẮT"
        reason_txt = self._format_reason(
            getattr(node, "auto_reason", {}).get(pump_idx, "")
        )

        if auto_type == "TIMER":
            schedules = getattr(node, "pump_schedule", {}).get(pump_idx, []) or []
            if schedules:
                first = schedules[0]
                if isinstance(first, dict):
                    time_txt = first.get("time")
                    duration = first.get("duration")
                else:
                    time_txt = getattr(first, "time", None)
                    duration = getattr(first, "duration", None)

                if time_txt and duration is not None:
                    return (
                        self.tr("Chế độ: HẸN GIỜ • {time} ({dur}p) • {state}").format(
                            time=time_txt,
                            dur=duration,
                            state=state_txt,
                        ),
                        "timer",
                        reason_txt,
                    )
            return (
                self.tr("Chế độ: HẸN GIỜ • {state}").format(state=state_txt),
                "timer",
                reason_txt,
            )

        next_sched = getattr(node, "next_schedule", {}).get(pump_idx)
        if isinstance(next_sched, (tuple, list)) and len(next_sched) >= 1:
            time_txt = next_sched[0]
            duration = next_sched[1] if len(next_sched) >= 2 else None

            if duration is None:
                return (
                    self.tr("Chế độ: LỊCH • {time} • {state}").format(
                        time=time_txt,
                        state=state_txt,
                    ),
                    "schedule",
                    reason_txt,
                )

            return (
                self.tr("Chế độ: LỊCH • {time} ({dur}p) • {state}").format(
                    time=time_txt,
                    dur=duration,
                    state=state_txt,
                ),
                "schedule",
                reason_txt,
            )

        return (
            self.tr("Chế độ: LỊCH • {state}").format(state=state_txt),
            "schedule",
            reason_txt,
        )

    def _refresh_test_button(self):
        node, pump_idx = self._active_pump_target()
        enabled = node is not None and pump_idx is not None
        self.test_btn.setEnabled(enabled)
        if not enabled:
            self.test_btn.setText(self.tr("Bật bơm"))
            return

        node.pump_state = getattr(node, "pump_state", {})
        state = node.pump_state.get(pump_idx, "OFF")
        if state == "ON":
            self.test_btn.setText(self.tr("Tắt bơm"))
        else:
            self.test_btn.setText(self.tr("Bật bơm"))

    def _on_test_water(self):
        node, pump_idx = self._active_pump_target()
        if not node or pump_idx is None:
            self.detailRequested.emit(self.zone.id)
            return

        node.pump_state = getattr(node, "pump_state", {})
        node.auto_reason = getattr(node, "auto_reason", {})
        current = node.pump_state.get(pump_idx, "OFF")
        cmd = "OFF" if current == "ON" else "ON"

        node.pump_state[pump_idx] = "ON" if cmd == "ON" else "OFF"
        if cmd == "ON":
            node.auto_reason[pump_idx] = "manual-start"
        else:
            node.auto_reason[pump_idx] = "manual-stop"

        self._update_metrics_and_status()
        self._refresh_test_button()

        if self.bus:
            self.bus.send_manual(node.id, pump_idx, cmd)

    def _format_reason(self, reason: str) -> str:
        text = (reason or "").strip().strip(",")
        if not text:
            return ""
        text = (
            text.replace("manual-start", "bật thủ công")
            .replace("manual-stop", "tắt thủ công")
            .replace("timer-start", "bắt đầu hẹn giờ")
            .replace("timer-stop(timeout)", "dừng hẹn giờ (hết thời gian)")
            .replace("immediate-stop:", "dừng tức thì:")
            .replace("immediate-dry", "khô tức thì")
            .replace("cooldown-override", "bỏ qua thời gian chờ")
            .replace("cooldown ", "đang chờ ")
            .replace(" remaining", " còn lại")
            .replace("sensor=no-moisture", "cảm biến không có dữ liệu ẩm đất")
            .replace("no crop", "chưa chọn cây")
            .replace("unknown crop", "cây không hợp lệ")
            .replace("daily quota reached", "đã đạt giới hạn ngày")
            .replace("already wet", "đất đã ẩm")
            .replace("rain_prob=", "xác suất mưa=")
            .replace("rain_mm=", "lượng mưa=")
            .replace("very_dry", "rất khô")
            .replace("dry", "khô")
            .replace("moist", "ẩm")
            .replace("hot", "nóng")
            .replace("cool", "mát")
            .replace("humid", "ẩm cao")
            .replace("rain-risk", "nguy cơ mưa")
            .replace("recovered", "đã phục hồi")
            .replace("timeout", "hết thời gian")
            .replace("crop=", "cây=")
        )
        if len(text) > 96:
            text = text[:93] + "..."
        return self.tr("Lý do: {reason}").format(reason=text)

    @staticmethod
    def _auto_type_label(auto_type: str) -> str:
        if auto_type == "TIMER":
            return "HẸN GIỜ"
        return "LỊCH"

    @staticmethod
    def _normalize_auto_type(value: str) -> str:
        if value == "RECOMMEND":
            return "SCHEDULE"
        if value in ("SCHEDULE", "TIMER"):
            return value
        return "SCHEDULE"

    @staticmethod
    def _as_float(value):
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
