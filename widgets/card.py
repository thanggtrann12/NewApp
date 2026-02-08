from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton,
    QGridLayout, QWidget, QSizePolicy
)
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QGraphicsDropShadowEffect


class NodeCard(QFrame):
    removeRequested = pyqtSignal(str)        # node_id
    detailRequested = pyqtSignal(str)        # node_id
    configChanged = pyqtSignal(str)
    # realtime command -> service -> ESP32
    pumpCommand = pyqtSignal(str, int, str)  # node_id, pump_idx, ON/OFF

    def __init__(self, node, parent=None):
        super().__init__(parent)
        self.node = node
        if not hasattr(self.node, "pump_mode"):
            self.node.pump_mode = {}

        if not hasattr(self.node, "auto_type"):
            self.node.auto_type = {}

        if not hasattr(self.node, "pump_schedule"):
            self.node.pump_schedule = {}
        # ================= CARD =================
        self.setObjectName("Card")
        self.setMinimumSize(320, 160)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.setFocusPolicy(Qt.NoFocus)

        # Shadow (nhẹ cho Pi 2)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(8)
        shadow.setColor(QColor(0, 0, 0, 120))
        shadow.setOffset(0, 3)
        self.setGraphicsEffect(shadow)

        # ================= ROOT =================
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(8)

        # ================= HEADER =================
        header = QHBoxLayout()

        title = QLabel(self.node.name or "ESP Node")
        title.setObjectName("CardTitle")

        close_btn = QPushButton("✕")
        close_btn.setObjectName("CloseButton")
        close_btn.setFixedSize(36, 36)
        close_btn.clicked.connect(
            lambda: self.removeRequested.emit(self.node.id)
        )

        header.addWidget(title, 1)
        header.addWidget(close_btn)

        # ================= PUMP LIST =================
        self.grid_widget = QWidget()
        self.grid = QGridLayout(self.grid_widget)
        self.grid.setContentsMargins(0, 4, 0, 0)
        self.grid.setHorizontalSpacing(12)
        self.grid.setVerticalSpacing(6)

        self._pump_rows = {}
        self._build_pump_list()

        # ================= FOOTER =================
        detail_btn = QPushButton("DETAIL")
        detail_btn.setObjectName("DetailButton")
        detail_btn.setFixedHeight(36)
        detail_btn.clicked.connect(
            lambda: self.detailRequested.emit(self.node.id)
        )

        # ================= ASSEMBLE =================
        root.addLayout(header)
        root.addWidget(self.grid_widget)
        root.addStretch(1)
        root.addWidget(detail_btn)

    # ==================================================
    # BUILD PUMP LIST
    # ==================================================
    def _build_pump_list(self):
        while self.grid.count():
            w = self.grid.takeAt(0).widget()
            if w:
                w.deleteLater()

        self._pump_rows.clear()

        pumps = getattr(self.node, "pumps", 0)
        if pumps <= 0:
            lbl = QLabel("No pumps connected")
            lbl.setObjectName("PumpEmpty")
            self.grid.addWidget(lbl, 0, 0)
            return

        for i in range(pumps):
            # ===== Pump label (click to config) =====
            pump_btn = QPushButton(f"Pump {i+1}")
            pump_btn.setObjectName("PumpButton")
            pump_btn.clicked.connect(
                lambda _, idx=i: self._open_config(idx)
            )

            # ===== Status / schedule label =====
            info_lbl = QLabel("-")
            info_lbl.setObjectName("PumpInfo")

            # ===== Manual control =====
            ctrl = QWidget()
            ctrl_lay = QHBoxLayout(ctrl)
            ctrl_lay.setContentsMargins(0, 0, 0, 0)
            ctrl_lay.setSpacing(8)

            on_btn = QPushButton("ON")
            off_btn = QPushButton("OFF")
            on_btn.setObjectName("PumpOn")
            off_btn.setObjectName("PumpOff")

            on_btn.clicked.connect(
                lambda _, idx=i: self._manual_cmd(idx, "ON")
            )
            off_btn.clicked.connect(
                lambda _, idx=i: self._manual_cmd(idx, "OFF")
            )

            ctrl_lay.addWidget(on_btn)
            ctrl_lay.addWidget(off_btn)
            ctrl.setVisible(False)

            row = i * 2
            self.grid.addWidget(pump_btn, row, 0, Qt.AlignLeft)
            self.grid.addWidget(info_lbl, row, 1, Qt.AlignLeft)
            self.grid.addWidget(ctrl, row + 1, 0, 1, 2)

            self._pump_rows[i] = (pump_btn, info_lbl, ctrl)
            self._update_pump_row(i)
            

    # ==================================================
    # UPDATE ROW (MODE + STATUS)
    # ==================================================
    def _update_pump_row(self, idx: int):
        pump_btn, info_lbl, ctrl = self._pump_rows[idx]

        pump_mode = getattr(self.node, "pump_mode", {}).get(idx, "AUTO")
        auto_type = getattr(self.node, "auto_type", {}).get(idx, "RECOMMEND")

        pump_state = getattr(self.node, "pump_state", {}).get(idx, "OFF")
        pump_schedule = getattr(self.node, "pump_schedule", {}).get(idx, [])
        next_sched = getattr(self.node, "next_schedule", {}).get(idx)
        auto_reason = getattr(self.node, "auto_reason", {}).get(idx)

        # ================= MANUAL =================
        if pump_mode == "MANUAL":
            pump_btn.setText(f"Pump {idx+1}  [MANUAL]")
            ctrl.setVisible(True)

            if pump_state == "ON":
                info_lbl.setText("● RUNNING")
                info_lbl.setProperty("state", "RUNNING")
            else:
                info_lbl.setText("OFF")
                info_lbl.setProperty("state", "OFF")

        # ================= AUTO =================
        else:
            ctrl.setVisible(False)

            # -------- AUTO + TIMER --------
            if auto_type == "TIMER" and pump_schedule:
                pump_btn.setText(f"Pump {idx+1}  [AUTO]")

                lines = []

                for item in pump_schedule:
                    if len(item) == 3:
                        t, d, days = item
                    else:
                        t, d = item
                        days = []

                    if days:
                        day_txt = ",".join(
                            ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"][i]
                            for i in days
                        )
                    else:
                        day_txt = "Every day"

                    lines.append(f"⏰ {t} ({d} min) · {day_txt}")

                info_lbl.setText("\n".join(lines))

            # -------- AUTO + RECOMMEND (computed) --------
            elif auto_type == "RECOMMEND" and next_sched:
                t, d = next_sched
                pump_btn.setText(f"Pump {idx+1}  [AUTO]")

                if auto_reason:
                    info_lbl.setText(f"{t} ({d} min) · {auto_reason}")
                else:
                    info_lbl.setText(f"{t} ({d} min)")

            # -------- AUTO + RECOMMEND (not computed yet) --------
            elif auto_type == "RECOMMEND":
                pump_btn.setText(f"Pump {idx+1}  [AUTO]")
                info_lbl.setText("Waiting for weather decision")

            # -------- AUTO skipped --------
            elif auto_reason:
                pump_btn.setText(f"Pump {idx+1}  [AUTO]")
                info_lbl.setText(f"Skipped · {auto_reason}")

            # -------- AUTO fallback --------
            else:
                pump_btn.setText(f"Pump {idx+1}  [AUTO]")
                info_lbl.setText("-")

            info_lbl.setProperty("state", "")

        # ================= REFRESH STYLE =================
        pump_btn.style().unpolish(pump_btn)
        pump_btn.style().polish(pump_btn)
        info_lbl.style().unpolish(info_lbl)
        info_lbl.style().polish(info_lbl)

    # ==================================================
    # OPEN CONFIG DIALOG
    # ==================================================
    def _open_config(self, idx: int):
        from dialogs.pump_control_dialog import PumpControlDialog

        dlg = PumpControlDialog(self.node, idx, self)
        if dlg.exec_():
            data = dlg.result_data()

            # ensure runtime fields
            if not hasattr(self.node, "pump_mode"):
                self.node.pump_mode = {}
            if not hasattr(self.node, "auto_type"):
                self.node.auto_type = {}
            if not hasattr(self.node, "pump_schedule"):
                self.node.pump_schedule = {}

            self.node.pump_mode[idx] = data["mode"]
            self.node.auto_type[idx] = data["auto_type"]
            self.node.pump_schedule[idx] = data["schedule"]
            self._update_pump_row(idx)
            self.configChanged.emit(self.node.id)

    # ==================================================
    # MANUAL COMMAND
    # ==================================================
    def _manual_cmd(self, idx: int, cmd: str):
        # optimistic UI update (optional)
        if not hasattr(self.node, "pump_state"):
            self.node.pump_state = {}

        self.node.pump_state[idx] = "ON" if cmd == "ON" else "OFF"
        self._update_pump_row(idx)
        # send realtime command
        self.pumpCommand.emit(self.node.id, idx, cmd)

    # ==================================================
    # CALLED BY SERVICE WHEN ESP32 REPORTS STATE
    # ==================================================
    def update_from_device(self, pump_idx, state, next_sched=None):
        # UI chưa build xong → ignore
        if pump_idx not in self._pump_rows:
            print(
                f"[UI] pump row {pump_idx} not ready, rebuild"
            )
            self._build_pump_list()
            if pump_idx not in self._pump_rows:
                return

        if not hasattr(self.node, "pump_state"):
            self.node.pump_state = {}

        self.node.pump_state[pump_idx] = state

        if next_sched:
            if not hasattr(self.node, "next_schedule"):
                self.node.next_schedule = {}
            self.node.next_schedule[pump_idx] = next_sched

        self._update_pump_row(pump_idx)
