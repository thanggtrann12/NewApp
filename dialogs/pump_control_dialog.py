from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QRadioButton,
    QGroupBox, QListWidget, QListWidgetItem,
    QTimeEdit, QCheckBox
)
from PyQt5.QtCore import Qt, QTime

from models.schedule import PumpSchedule


class PumpControlDialog(QDialog):
    def __init__(self, node, pump_idx: int, crop_registry=None, parent=None):
        super().__init__(parent)
        self.node = node
        self.pump_idx = pump_idx
        self.crop_registry = crop_registry

        self.setWindowTitle(
            self.tr("Điều khiển bơm {n}").format(n=pump_idx + 1)
        )
        self.setModal(True)
        self.setMinimumWidth(360)

        crop_id = node.pump_crop_map.get(pump_idx)
        crop = crop_registry.get(crop_id) if crop_registry else None
        crop_name = crop.name if crop else (crop_id or self.tr("Chưa đặt"))

        # ================= ROOT =================
        root = QVBoxLayout(self)
        root.setSpacing(10)

        title = QLabel(self.tr("Bơm {n}").format(n=pump_idx + 1))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size:14pt;font-weight:600;")
        root.addWidget(title)

        root.addWidget(
            QLabel(self.tr("Cây trồng: {crop}").format(crop=crop_name))
        )

        # ================= AUTOMATION TYPE =================
        self.auto_box = QGroupBox(self.tr("Tự động hóa"))
        auto_layout = QVBoxLayout(self.auto_box)

        self.auto_schedule_radio = QRadioButton(
            self.tr("Lịch (theo cây trồng)")
        )
        self.timer_radio = QRadioButton(
            self.tr("Hẹn giờ (tùy chỉnh)")
        )

        auto_type = self._normalize_auto_type(
            getattr(node, "auto_type", {}).get(pump_idx, "SCHEDULE")
        )
        self.auto_schedule_radio.setChecked(auto_type == "SCHEDULE")
        self.timer_radio.setChecked(auto_type == "TIMER")
        if not self.auto_schedule_radio.isChecked() and not self.timer_radio.isChecked():
            self.auto_schedule_radio.setChecked(True)

        auto_layout.addWidget(self.auto_schedule_radio)
        auto_layout.addWidget(self.timer_radio)

        # ================= TIMER UI =================
        self.timer_list = QListWidget()
        self.timer_list.setFixedHeight(110)

        DAY_NAMES = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]

        schedules = getattr(node, "pump_schedule", {}).get(pump_idx, [])

        # ===== LOAD EXISTING SCHEDULES =====
        for sch in schedules:
            if not isinstance(sch, PumpSchedule):
                continue

            t = sch.time
            d = sch.duration
            days = sch.days or []

            if days:
                day_txt = ",".join(DAY_NAMES[i] for i in days)
                text = f"{t} – {d} phút · {day_txt}"
            else:
                text = f"{t} – {d} phút · Mỗi ngày"

            item = QListWidgetItem(text, self.timer_list)
            item.setData(
                Qt.UserRole,
                PumpSchedule(time=t, duration=d, days=days)
            )

        btn_row = QHBoxLayout()
        self.add_timer_btn = QPushButton(self.tr("Thêm hẹn giờ"))
        self.del_timer_btn = QPushButton(self.tr("Xóa"))
        self.add_timer_btn.clicked.connect(self._add_timer)
        self.del_timer_btn.clicked.connect(self._remove_timer)
        btn_row.addWidget(self.add_timer_btn)
        btn_row.addWidget(self.del_timer_btn)

        auto_layout.addWidget(self.timer_list)
        auto_layout.addLayout(btn_row)

        root.addWidget(self.auto_box)

        # ================= FOOTER =================
        footer = QHBoxLayout()
        save_btn = QPushButton(self.tr("LƯU"))
        cancel_btn = QPushButton(self.tr("HỦY"))
        save_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        footer.addStretch(1)
        footer.addWidget(cancel_btn)
        footer.addWidget(save_btn)
        root.addLayout(footer)

        # ================= VISIBILITY =================
        self._update_visibility()
        self.timer_radio.toggled.connect(self._update_visibility)

    # ================= LOGIC =================
    def _update_visibility(self):
        timer_mode = self.timer_radio.isChecked()
        self.timer_list.setEnabled(timer_mode)
        self.add_timer_btn.setEnabled(timer_mode)
        self.del_timer_btn.setEnabled(timer_mode)

    def _add_timer(self):
        dlg = QDialog(self)
        dlg.setWindowTitle(self.tr("Thêm hẹn giờ"))

        lay = QVBoxLayout(dlg)

        time_edit = QTimeEdit(QTime.currentTime())
        time_edit.setDisplayFormat("HH:mm")
        lay.addWidget(QLabel(self.tr("Giờ bắt đầu")))
        lay.addWidget(time_edit)

        dur_edit = QTimeEdit(QTime(0, 10))
        dur_edit.setDisplayFormat("mm")
        lay.addWidget(QLabel(self.tr("Thời lượng (phút)")))
        lay.addWidget(dur_edit)

        days_box = QGroupBox(self.tr("Lặp vào"))
        days_lay = QHBoxLayout(days_box)
        day_checks = []
        labels = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]

        for i, lbl in enumerate(labels):
            cb = QCheckBox(lbl)
            day_checks.append(cb)
            days_lay.addWidget(cb)

        lay.addWidget(days_box)

        ok = QPushButton(self.tr("Đồng ý"))
        ok.clicked.connect(dlg.accept)
        lay.addWidget(ok)

        if dlg.exec_():
            t = time_edit.time().toString("HH:mm")
            d = dur_edit.time().minute()
            days = [i for i, cb in enumerate(day_checks) if cb.isChecked()]

            sch = PumpSchedule(time=t, duration=d, days=days)

            label = f"{t} – {d} phút"
            if days:
                label += " · " + ",".join(labels[i] for i in days)

            item = QListWidgetItem(label, self.timer_list)
            item.setData(Qt.UserRole, sch)

    def _remove_timer(self):
        row = self.timer_list.currentRow()
        if row >= 0:
            self.timer_list.takeItem(row)

    # ================= RESULT =================
    def result_data(self):
        mode = "AUTO"
        auto_type = (
            "TIMER"
            if self.timer_radio.isChecked()
            else "SCHEDULE"
        )

        schedules = []
        for i in range(self.timer_list.count()):
            item = self.timer_list.item(i)
            sch = item.data(Qt.UserRole)
            if isinstance(sch, PumpSchedule):
                schedules.append(sch)

        return {
            "mode": mode,
            "auto_type": auto_type,
            "schedule": schedules
        }

    @staticmethod
    def _normalize_auto_type(value: str) -> str:
        if value == "RECOMMEND":
            return "SCHEDULE"
        if value in ("SCHEDULE", "TIMER"):
            return value
        return "SCHEDULE"
