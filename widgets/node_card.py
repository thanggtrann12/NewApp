from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QWidget, QSizePolicy,
    QGraphicsDropShadowEffect, QGridLayout
)
from PyQt5.QtGui import QColor
from models.schedule import PumpSchedule

class NodeCard(QFrame):
    removeRequested = pyqtSignal(str)
    detailRequested = pyqtSignal(str)
    configChanged = pyqtSignal(str)

    def __init__(self, node, crop_registry, bus, parent=None):
        super().__init__(parent)
        self.node = node
        self.crop_registry = crop_registry
        self.bus = bus
        # ===== ensure attrs =====
        self.node.pump_mode = getattr(self.node, "pump_mode", {})
        self.node.auto_type = getattr(self.node, "auto_type", {})
        self.node.pump_schedule = getattr(self.node, "pump_schedule", {})
        self.node.pump_state = getattr(self.node, "pump_state", {})
        self.node.next_schedule = getattr(self.node, "next_schedule", {})
        self.node.auto_reason = getattr(self.node, "auto_reason", {})
        self.node.pump_crop_map = getattr(self.node, "pump_crop_map", {})

        self.setObjectName("Card")
        self.setMinimumWidth(320)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(8)
        shadow.setColor(QColor(0, 0, 0, 120))
        shadow.setOffset(0, 3)
        self.setGraphicsEffect(shadow)

        # ===== ROOT =====
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        # ===== HEADER =====
        header = QHBoxLayout()
        title = QLabel(self.node.name or self.tr("ESP Node"))
        title.setObjectName("CardTitle")

        close_btn = QPushButton("✕")  # icon, không i18n
        close_btn.setObjectName("CloseButton")
        close_btn.setFixedSize(36, 36)
        close_btn.clicked.connect(
            lambda: self.removeRequested.emit(self.node.id)
        )

        header.addWidget(title, 1)
        header.addWidget(close_btn)

        # ===== PUMP LIST =====
        self.list_widget = QWidget()
        self.list_layout = QGridLayout(self.list_widget)
        self.list_layout.setContentsMargins(0, 4, 0, 0)
        self.list_layout.setHorizontalSpacing(12)
        self.list_layout.setVerticalSpacing(8)
        self._pump_rows = {}
        self._build_pump_list()

        # ===== FOOTER =====
        detail_btn = QPushButton(self.tr("DETAIL"))
        detail_btn.setObjectName("DetailButton")
        detail_btn.setFixedHeight(36)
        detail_btn.clicked.connect(
            lambda: self.detailRequested.emit(self.node.id)
        )

        root.addLayout(header)
        root.addWidget(self.list_widget)
        root.addStretch(1)
        root.addWidget(detail_btn)

    # ==================================================
    # BUILD PUMP LIST
    # ==================================================
    def _build_pump_list(self):
        # ===== CLEAR OLD ITEMS =====
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        self._pump_rows.clear()

        pumps = int(getattr(self.node, "pumps", 0))
        if pumps <= 0:
            lbl = QLabel(self.tr("No pumps connected"))
            lbl.setAlignment(Qt.AlignCenter)
            self.list_layout.addWidget(lbl, 0, 0, 1, 4)
            return

        # ===== GRID CONFIG (SET ONCE) =====
        self.list_layout.setHorizontalSpacing(12)
        self.list_layout.setVerticalSpacing(8)
        self.list_layout.setColumnStretch(1, 1)          # TIME column
        self.list_layout.setColumnMinimumWidth(2, 120)   # REASON column

        # ===== BUILD ROWS =====
        for i in range(pumps):
            # ---- pump button ----
            pump_btn = QPushButton()
            pump_btn.setObjectName("PumpButton")
            pump_btn.setFixedHeight(28)
            pump_btn.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
            pump_btn.clicked.connect(
                lambda _, idx=i: self._open_config(idx)
            )

            # ---- main info (time / schedule) ----
            info_main = QLabel("-")
            info_main.setObjectName("PumpInfoMain")
            info_main.setFixedHeight(20)
            info_main.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            info_main.setSizePolicy(
                QSizePolicy.Expanding, QSizePolicy.Fixed
            )

            # ---- reason / status ----
            info_reason = QLabel("")
            info_reason.setObjectName("PumpInfoReason")
            info_reason.setFixedHeight(20)
            info_reason.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            info_reason.setStyleSheet("color:#9aa0a6;")

            # ---- manual control ----
            ctrl = QWidget()
            ctrl_lay = QHBoxLayout(ctrl)
            ctrl_lay.setContentsMargins(0, 0, 0, 0)
            ctrl_lay.setSpacing(8)

            on_btn = QPushButton(self.tr("ON"))
            off_btn = QPushButton(self.tr("OFF"))
            on_btn.setObjectName("PumpOn")
            off_btn.setObjectName("PumpOff")
            on_btn.setFixedSize(64, 28)
            off_btn.setFixedSize(64, 28)

            on_btn.clicked.connect(
                lambda _, idx=i: self._manual_cmd(idx, "ON")
            )
            off_btn.clicked.connect(
                lambda _, idx=i: self._manual_cmd(idx, "OFF")
            )

            ctrl_lay.addWidget(on_btn)
            ctrl_lay.addWidget(off_btn)
            ctrl.setVisible(False)

            # ===== ADD TO GRID (ROW i) =====
            self.list_layout.addWidget(pump_btn,    i, 0, Qt.AlignVCenter)
            self.list_layout.addWidget(info_main,   i, 1)
            self.list_layout.addWidget(info_reason, i, 2)
            self.list_layout.addWidget(ctrl,        i, 3, Qt.AlignVCenter)

            # ===== STORE REFERENCES =====
            self._pump_rows[i] = (
                pump_btn,
                info_main,
                info_reason,
                ctrl
            )

            # ===== INITIAL UPDATE =====
            self._update_pump_row(i)

    # ==================================================
    # UPDATE ROW
    # ==================================================
    def _update_pump_row(self, idx: int):
        if idx not in self._pump_rows:
            return

        pump_btn, info_main, info_reason, ctrl = self._pump_rows[idx]

        pump_mode = self.node.pump_mode.get(idx, "AUTO")
        auto_type = self.node.auto_type.get(idx, "RECOMMEND")
        pump_state = self.node.pump_state.get(idx, "OFF")
        schedules = self.node.pump_schedule.get(idx, [])
        next_sched = self.node.next_schedule.get(idx)
        auto_reason = self.node.auto_reason.get(idx)

        crop_id = self.node.pump_crop_map.get(idx)
        crop = self.crop_registry.get(crop_id)
        crop_txt = f" {crop.name}" if crop else ""

        if pump_mode == "MANUAL":
            pump_btn.setText(
                self.tr("Pump {n} [MANUAL]{crop}")
                .format(n=idx + 1, crop=crop_txt)
            )
            ctrl.setVisible(True)
            info_main.setText(
                self.tr("● RUNNING") if pump_state == "ON"
                else self.tr("● OFF")
            )
            info_reason.setText("")
        else:
            pump_btn.setText(
                self.tr("Pump {n} [AUTO]{crop}")
                .format(n=idx + 1, crop=crop_txt)
            )
            ctrl.setVisible(False)

            if auto_type == "TIMER" and schedules:
                sch = schedules[0]
                t, d = sch.time, sch.duration
                info_main.setText(
                    self.tr("⏰ {time} ({min} min)")
                    .format(time=t, min=d)
                )
                info_reason.setText("")
            elif auto_type == "RECOMMEND" and next_sched:
                t, d = next_sched
                info_main.setText(
                    self.tr("🌦 {time} ({min} min)")
                    .format(time=t, min=d)
                )
                info_reason.setText(auto_reason or "")
            elif auto_reason:
                info_main.setText(self.tr("⛔ Skipped"))
                info_reason.setText(auto_reason)
            else:
                info_main.setText("-")
                info_reason.setText("")

        # ---- elide ----
        info_main.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed
        )

        info_reason.setSizePolicy(
            QSizePolicy.Maximum,
            QSizePolicy.Fixed
        )
        info_main.setTextInteractionFlags(Qt.NoTextInteraction)
        info_reason.setTextInteractionFlags(Qt.NoTextInteraction)

        pump_btn.adjustSize()
        info_reason.setCursor(Qt.PointingHandCursor)
        info_reason.mousePressEvent = (
            lambda e, idx=idx: self._open_auto_debug(idx)
        )
    # ==================================================
    # ACTIONS
    # ==================================================
    def _open_config(self, idx: int):
        from dialogs.pump_control_dialog import PumpControlDialog
        dlg = PumpControlDialog(self.node, idx, self)
        if dlg.exec_():
            data = dlg.result_data()
            self.node.pump_mode[idx] = data["mode"]
            self.node.auto_type[idx] = data["auto_type"]
            self.node.pump_schedule[idx] = data["schedule"]
            self._update_pump_row(idx)
            self.configChanged.emit(self.node.id)

    def _manual_cmd(self, idx: int, cmd: str):
        self.node.pump_state[idx] = "ON" if cmd == "ON" else "OFF"
        self._update_pump_row(idx)
        # self.onPumActionRequested.emit(self.node.id, idx, cmd)
        self.bus.send_manual(self.node.id, idx, cmd)

    def update_from_device(self, pump_idx, state, next_sched=None):
        if pump_idx not in self._pump_rows:
            self._build_pump_list()
        self.node.pump_state[pump_idx] = state
        if next_sched:
            self.node.next_schedule[pump_idx] = next_sched
        self._update_pump_row(pump_idx)

    def _open_auto_debug(self, idx: int):
        if not hasattr(self.node, "_last_auto_decision"):
            return

        decision = self.node._last_auto_decision.get(idx)
        if not decision:
            return

        weather = getattr(self.node, "_last_weather", {})
        crop_id = self.node.pump_crop_map.get(idx)
        crop = self.crop_registry.get(crop_id)

        from dialogs.auto_debug_dialog import AutoDebugDialog
        dlg = AutoDebugDialog(
            self.node,
            idx,
            crop,
            weather,
            decision,
            self
        )
        dlg.exec_()