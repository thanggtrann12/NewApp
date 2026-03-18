from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QLabel
)
from PyQt5.QtCore import (
    QTimer, Qt
)
from datetime import datetime


class StatusBar(QWidget):
    def __init__(self, store, bus, main_window, parent=None):
        super().__init__(parent)
        self.setObjectName("TopStatusBar")
        self.store = store
        self.bus = bus
        self.main_window = main_window

        # ===============================
        # UI
        # ===============================
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 6, 12, 6)
        lay.setSpacing(16)

        self.time_lbl = QLabel()
        self.time_lbl.setObjectName("StatusTime")
        self.time_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.net_lbl = QLabel(self.tr("Wi-Fi: -"))
        self.net_lbl.setObjectName("StatusBadge")
        self.gw_lbl = QLabel(self.tr("Gateway: -"))
        self.gw_lbl.setObjectName("StatusBadge")
        self.auto_lbl = QLabel()
        self.auto_lbl.setObjectName("StatusBadge")

        lay.addStretch(1)
        lay.addWidget(self.time_lbl)

        # ===============================
        # TIME UPDATE
        # ===============================
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_time)
        self.timer.start(1_000)  # mỗi giây
        self._update_time()
        self.set_auto(False)

    # ===============================
    # TIME
    # ===============================
    def _update_time(self):
        self.time_lbl.setText(
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

    # ===============================
    # STATUS API
    # ===============================
    def set_gateway(self, ok: bool):
        self.gw_lbl.setText(
            self.tr("Gateway: KẾT NỐI")
            if ok else
            self.tr("Gateway: MẤT KẾT NỐI")
        )

    def set_auto(self, enabled: bool):
        self.auto_lbl.setText(
            self.tr("Tự động: BẬT")
            if enabled else
            self.tr("Tự động: TẮT")
        )

    def set_wifi(self, text: str):
        self.net_lbl.setText(self.tr("Wi-Fi: {0}").format(text))

