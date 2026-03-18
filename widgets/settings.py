from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QGroupBox, QCheckBox,
    QPushButton, QMessageBox
)
from PyQt5.QtCore import QTimer

# Nếu bạn đã có NetworkService thì import
# Nếu chưa có, comment dòng này và xem NOTE bên dưới
from services.network_service import NetworkService


class SettingsPage(QWidget):
    """
    Settings Page v2
    - DEBUG: log filter
    - WIFI: master current wifi status + change button
    """

    def __init__(self, settings_service, parent=None):
        super().__init__(parent)
        self.settings = settings_service

        # ===== NETWORK SERVICE (MASTER ONLY) =====
        try:
            self.net = NetworkService(self)
        except Exception:
            self.net = None  # fallback nếu chưa implement

        # ===== ROOT =====
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(16)

        title = QLabel(self.tr("Cài đặt"))
        title.setObjectName("AppTitle")
        root.addWidget(title)

        # ==================================================
        # DEBUG SECTION
        # ==================================================
        debug_box = QGroupBox(self.tr("GỠ LỖI · Lọc log"))
        debug_lay = QVBoxLayout(debug_box)
        debug_lay.setSpacing(8)

        self.chk_debug_enable = QCheckBox(self.tr("Bật chế độ gỡ lỗi"))
        self.chk_debug_enable.setChecked(
            self.settings.data.get("debug", {}).get("enabled", False)
        )
        debug_lay.addWidget(self.chk_debug_enable)

        self.chk_auto_timer = QCheckBox("Bộ hẹn giờ tự động")
        self.chk_auto_decision = QCheckBox("Quyết định tự động")
        self.chk_bus = QCheckBox("Bus trung tâm")
        self.chk_serial = QCheckBox("Kết nối Serial")
        self.chk_weather = QCheckBox("Thời tiết")

        dbg = self.settings.data.get("debug", {})
        self.chk_auto_timer.setChecked(dbg.get("auto_timer", False))
        self.chk_auto_decision.setChecked(dbg.get("auto_decision", False))
        self.chk_bus.setChecked(dbg.get("bus", False))
        self.chk_serial.setChecked(dbg.get("serial", False))
        self.chk_weather.setChecked(dbg.get("weather", False))

        debug_lay.addWidget(self.chk_auto_timer)
        debug_lay.addWidget(self.chk_auto_decision)
        debug_lay.addWidget(self.chk_bus)
        debug_lay.addWidget(self.chk_serial)
        debug_lay.addWidget(self.chk_weather)

        root.addWidget(debug_box)

        # ==================================================
        # WIFI SECTION (MASTER ONLY)
        # ==================================================
        wifi_box = QGroupBox(self.tr("WIFI · Bộ điều khiển"))
        wifi_lay = QVBoxLayout(wifi_box)
        wifi_lay.setSpacing(6)

        self.lbl_wifi_ssid = QLabel("SSID: -")
        self.lbl_wifi_ip = QLabel("IP: -")
        self.lbl_wifi_signal = QLabel("Tín hiệu: -")
        self.lbl_wifi_status = QLabel("Trạng thái: Chưa xác định")

        wifi_lay.addWidget(self.lbl_wifi_ssid)
        wifi_lay.addWidget(self.lbl_wifi_ip)
        wifi_lay.addWidget(self.lbl_wifi_signal)
        wifi_lay.addWidget(self.lbl_wifi_status)

        pwd_row = QHBoxLayout()
        pwd_row.addWidget(QLabel("Mật khẩu: ********"))
        pwd_row.addStretch(1)
        self.btn_change_wifi = QPushButton(self.tr("Đổi Wi-Fi"))
        pwd_row.addWidget(self.btn_change_wifi)
        wifi_lay.addLayout(pwd_row)

        root.addWidget(wifi_box)

        # ==================================================
        # ACTION BUTTONS
        # ==================================================
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        btn_apply = QPushButton(self.tr("Áp dụng"))
        btn_apply.clicked.connect(self._apply)

        btn_row.addWidget(btn_apply)
        root.addLayout(btn_row)

        root.addStretch(1)

        # ==================================================
        # WIFI STATUS REFRESH
        # ==================================================
        if self.net:
            self._update_wifi_status()
            self.timer = QTimer(self)
            self.timer.timeout.connect(self._update_wifi_status)
            self.timer.start(5000)  # refresh mỗi 5s
        else:
            self.lbl_wifi_status.setText("Trạng thái: Chưa có NetworkService")

        self.btn_change_wifi.clicked.connect(self._change_wifi)

    # ==================================================
    # APPLY SETTINGS
    # ==================================================
    def _apply(self):
        new_debug = {
            "enabled": self.chk_debug_enable.isChecked(),
            "auto_timer": self.chk_auto_timer.isChecked(),
            "auto_decision": self.chk_auto_decision.isChecked(),
            "bus": self.chk_bus.isChecked(),
            "serial": self.chk_serial.isChecked(),
            "weather": self.chk_weather.isChecked(),
        }

        self.settings.update({
            "debug": new_debug
        })

        QMessageBox.information(
            self,
            self.tr("Cài đặt"),
            self.tr("Áp dụng cài đặt thành công.")
        )

    # ==================================================
    # WIFI
    # ==================================================
    def _update_wifi_status(self):
        if not self.net:
            return

        st = self.net.get_status()

        if not st:
            self.lbl_wifi_status.setText("Trạng thái: Chưa xác định")
            return

        ssid = st.get("ssid", "-")
        ip = st.get("ip", "-")
        signal = st.get("signal", "-")
        connected = st.get("connected", False)

        self.lbl_wifi_ssid.setText(f"SSID: {ssid}")
        self.lbl_wifi_ip.setText(f"IP: {ip}")
        self.lbl_wifi_signal.setText(f"Tín hiệu: {signal}")

        if connected:
            self.lbl_wifi_status.setText("Trạng thái: Đã kết nối")
            self.lbl_wifi_status.setStyleSheet("color:#4CAF50;")
        else:
            self.lbl_wifi_status.setText("Trạng thái: Mất kết nối")
            self.lbl_wifi_status.setStyleSheet("color:#E57373;")

    def _change_wifi(self):
        from dialogs.wifi_settings_dialog import WiFiSettingsDialog
        dlg = WiFiSettingsDialog(self)
        dlg.exec_()
