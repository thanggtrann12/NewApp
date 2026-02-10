from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QRadioButton,
    QGroupBox, QListWidget, QListWidgetItem,
    QTimeEdit, QCheckBox
)
from PyQt5.QtCore import Qt, QTime


class PumpControlDialog(QDialog):
    def __init__(self, node, pump_idx: int, parent=None):
        super().__init__(parent)
        self.node = node
        self.pump_idx = pump_idx

        self.setWindowTitle(self.tr("Pump {n} Control").format(n=pump_idx + 1))
        self.setModal(True)
        self.setMinimumWidth(340)

        crop = node.pump_crop_map.get(pump_idx, "Unknown")

        # ================= ROOT =================
        root = QVBoxLayout(self)
        root.setSpacing(10)

        title = QLabel(self.tr("Pump {n}").format(n=pump_idx + 1))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size:14pt;font-weight:600;")
        root.addWidget(title)

        root.addWidget(QLabel(self.tr("Crop: {crop}").format(crop=crop)))

        # ================= MODE =================
        self.manual_radio = QRadioButton(self.tr("MANUAL"))
        self.auto_radio = QRadioButton(self.tr("AUTO"))

        mode = getattr(node, "pump_mode", {}).get(pump_idx, "AUTO")
        self.manual_radio.setChecked(mode == "MANUAL")
        self.auto_radio.setChecked(mode == "AUTO")

        root.addWidget(self.manual_radio)
        root.addWidget(self.auto_radio)

        # ================= AUTO TYPE =================
        self.auto_box = QGroupBox(self.tr("AUTO Mode"))
        auto_layout = QVBoxLayout(self.auto_box)

        self.auto_rec_radio = QRadioButton(self.tr("Recommended (by crop)"))
        self.auto_timer_radio = QRadioButton(self.tr("Timer (set by you)"))

        auto_type = getattr(node, "auto_type", {}).get(
            pump_idx, "RECOMMEND"
        )

        self.auto_rec_radio.setChecked(auto_type == "RECOMMEND")
        self.auto_timer_radio.setChecked(auto_type == "TIMER")

        auto_layout.addWidget(self.auto_rec_radio)
        auto_layout.addWidget(self.auto_timer_radio)

        # ================= TIMER UI =================
        self.timer_list = QListWidget()
        self.timer_list.setFixedHeight(90)

        # ===== BUILD SCHEDULES =====
        schedules = getattr(node, "pump_schedule", {}).get(pump_idx, [])

        DAY_NAMES = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]

        for sch in schedules:
            if not isinstance(sch, dict):
                continue

            t = sch.get("time")
            d = sch.get("duration")
            days = sch.get("meta", {}).get("days", [])

            if days:
                day_txt = ",".join(
                    DAY_NAMES[i] if isinstance(i, int) else str(i)
                    for i in days
                )
                text = f"{t} – {d} min · {day_txt}"
            else:
                text = f"{t} – {d} min · Every day"

            item = QListWidgetItem(text, self.timer_list)
            item.setData(Qt.UserRole, (t, d, days))   # ✅ Gán dữ liệu

        btn_row = QHBoxLayout()
        add_timer_btn = QPushButton(self.tr("Add Timer"))
        del_timer_btn = QPushButton(self.tr("Remove"))
        add_timer_btn.clicked.connect(self._add_timer)
        del_timer_btn.clicked.connect(self._remove_timer)
        btn_row.addWidget(add_timer_btn)
        btn_row.addWidget(del_timer_btn)

        auto_layout.addWidget(self.timer_list)
        auto_layout.addLayout(btn_row)

        root.addWidget(self.auto_box)

        # ================= FOOTER =================
        footer = QHBoxLayout()
        save_btn = QPushButton(self.tr("SAVE"))
        cancel_btn = QPushButton(self.tr("CANCEL"))
        save_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        footer.addStretch(1)
        footer.addWidget(cancel_btn)
        footer.addWidget(save_btn)
        root.addLayout(footer)

        # ================= VISIBILITY =================
        self._update_visibility()
        self.manual_radio.toggled.connect(self._update_visibility)
        self.auto_timer_radio.toggled.connect(self._update_visibility)

    # ================= LOGIC =================
    def _update_visibility(self):
        self.auto_box.setVisible(self.auto_radio.isChecked())
        self.timer_list.setEnabled(self.auto_timer_radio.isChecked())

    def _add_timer(self):
        dlg = QDialog(self)
        dlg.setWindowTitle(self.tr("Add Timer"))

        lay = QVBoxLayout(dlg)
        time_edit = QTimeEdit(QTime.currentTime())
        time_edit.setDisplayFormat("HH:mm")
        lay.addWidget(QLabel(self.tr("Start time")))
        lay.addWidget(time_edit)

        dur_edit = QTimeEdit(QTime(0, 10))
        dur_edit.setDisplayFormat("mm")
        lay.addWidget(QLabel(self.tr("Duration (min)")))
        lay.addWidget(dur_edit)

        days_box = QGroupBox(self.tr("Repeat on"))
        days_lay = QHBoxLayout(days_box)
        day_checks = []
        labels = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]

        for i, lbl in enumerate(labels):
            cb = QCheckBox(lbl)
            day_checks.append(cb)
            days_lay.addWidget(cb)

        lay.addWidget(days_box)

        ok = QPushButton(self.tr("OK"))
        ok.clicked.connect(dlg.accept)
        lay.addWidget(ok)

        if dlg.exec_():
            t = time_edit.time().toString("HH:mm")
            d = dur_edit.time().minute()
            days = [i for i, cb in enumerate(day_checks) if cb.isChecked()]

            label = f"{t} – {d} min"
            if days:
                label += " · " + ",".join(labels[i] for i in days)

            item = QListWidgetItem(label, self.timer_list)
            item.setData(Qt.UserRole, (t, d, days))   # ✅ Gán dữ liệu

    def _remove_timer(self):
        row = self.timer_list.currentRow()
        if row >= 0:
            self.timer_list.takeItem(row)

    def result_data(self):
        mode = "MANUAL" if self.manual_radio.isChecked() else "AUTO"
        auto_type = "TIMER" if self.auto_timer_radio.isChecked() else "RECOMMEND"

        schedules = []
        for i in range(self.timer_list.count()):
            item = self.timer_list.item(i)
            data = item.data(Qt.UserRole)
            if data is not None:
                t, d, days = data
                schedules.append((t, d, days))
        return {
            "mode": mode,
            "auto_type": auto_type,
            "schedule": schedules
        }
