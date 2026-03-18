from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit,
    QCheckBox, QMessageBox, QSizePolicy
)
from PyQt5.QtCore import Qt

from services.network_service import NetworkService


class WiFiSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.net = NetworkService(self)
        self.net.statusChanged.connect(self._update_status)

        self.setWindowTitle("Cài đặt Wi-Fi (Bộ điều khiển)")
        self.setModal(True)

        # ================= ROOT =================
        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(20, 20, 20, 20)

        # ================= STATUS =================
        self.status_lbl = QLabel("Trạng thái: Chưa xác định")
        self.status_lbl.setAlignment(Qt.AlignLeft)
        root.addWidget(self.status_lbl)

        # ================= SSID =================
        root.addWidget(QLabel("SSID"))
        self.ssid_edit = QLineEdit()
        self.ssid_edit.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed
        )
        root.addWidget(self.ssid_edit)

        # ================= PASSWORD =================
        root.addWidget(QLabel("Mật khẩu"))
        self.pass_edit = QLineEdit()
        self.pass_edit.setEchoMode(QLineEdit.Password)
        self.pass_edit.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed
        )
        root.addWidget(self.pass_edit)

        self.show_pass = QCheckBox("Hiện mật khẩu")
        self.show_pass.toggled.connect(
            lambda v: self.pass_edit.setEchoMode(
                QLineEdit.Normal if v else QLineEdit.Password
            )
        )
        root.addWidget(self.show_pass)
        self.ssid_edit.returnPressed.connect(self._apply)
        self.pass_edit.returnPressed.connect(self._apply)

        # ⬇⬇⬇ ĐÂY là dòng quan trọng để không bị stretch ⬇⬇⬇
        root.addStretch(1)

        # ================= ACTIONS =================
        btns = QHBoxLayout()
        btns.addStretch(1)

        cancel = QPushButton("Hủy")
        apply = QPushButton("Áp dụng")

        cancel.clicked.connect(self.reject)
        apply.clicked.connect(self._apply)

        btns.addWidget(cancel)
        btns.addWidget(apply)
        root.addLayout(btns)

        # ================= INIT =================
        self._update_status(self.net.get_status())
        self.adjustSize()          # fit đúng nội dung
        self.setFixedSize(800, 520)  # không bị quá hẹp

    # ================= LOGIC =================
    def _update_status(self, status: dict):
        if status.get("connected"):
            self.status_lbl.setText(
                f"Trạng thái: Đã kết nối ({status.get('ssid')})"
            )
            self.status_lbl.setStyleSheet("color:#4CAF50;")
            self.ssid_edit.setText(status.get("ssid", ""))
        else:
            self.status_lbl.setText("Trạng thái: Mất kết nối")
            self.status_lbl.setStyleSheet("color:#E57373;")

    def _apply(self):
        ssid = self.ssid_edit.text().strip()
        pwd = self.pass_edit.text()

        if not ssid:
            QMessageBox.warning(self, "Wi-Fi", "Vui lòng nhập SSID")
            return

        self.status_lbl.setText("Đang áp dụng…")
        self.status_lbl.setStyleSheet("color:#FFB300;")

        ok = self.net.connect_wifi(ssid, pwd)
        if not ok:
            QMessageBox.critical(
                self,
                "Wi-Fi",
                "Kết nối thất bại. Vui lòng kiểm tra thông tin đăng nhập."
            )
