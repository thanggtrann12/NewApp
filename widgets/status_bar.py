from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt5.QtCore import QTimer
from datetime import datetime


class StatusBar(QWidget):
    def __init__(self, store, bus, parent=None):
        super().__init__(parent)
        self.store = store
        self.bus = bus

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 6, 12, 6)
        lay.setSpacing(16)

        self.time_lbl = QLabel()
        self.net_lbl = QLabel("📶 WiFi: -")
        self.gw_lbl = QLabel("🔗 Gateway: -")
        self.auto_lbl = QLabel("🤖 AUTO")

        lay.addWidget(self.time_lbl)
        lay.addStretch(1)
        lay.addWidget(self.net_lbl)
        lay.addWidget(self.gw_lbl)
        lay.addWidget(self.auto_lbl)

        # update time
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_time)
        self.timer.start(60_000)
        self._update_time()

    def _update_time(self):
        self.time_lbl.setText(
            "⏰ " + datetime.now().strftime("%H:%M")
        )

    # ===== APIs cho service gọi =====
    def set_wifi(self, level: str):
        self.net_lbl.setText(f"📶 WiFi: {level}")

    def set_gateway(self, ok: bool):
        self.gw_lbl.setText(
            "🔗 Gateway: OK" if ok else "🔴 Gateway: Down"
        )

    def set_auto(self, enabled: bool):
        self.auto_lbl.setText(
            "🤖 AUTO" if enabled else "⚠️ AUTO PAUSED"
        )
