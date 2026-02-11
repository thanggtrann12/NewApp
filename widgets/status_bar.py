from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton
)
from PyQt5.QtCore import (
    Qt, QTimer, QEvent
)
from datetime import datetime


class StatusBar(QWidget):
    def __init__(self, store, bus, lang_service, parent=None):
        super().__init__(parent)
        self.store = store
        self.bus = bus
        self.lang_service = lang_service

        # ===============================
        # UI
        # ===============================
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 6, 12, 6)
        lay.setSpacing(16)

        self.time_lbl = QLabel()
        self.net_lbl = QLabel("📶 -")
        self.gw_lbl = QLabel("🔗 -")
        self.auto_lbl = QLabel()

        # 🌐 language toggle button (flag)
        self.lang_btn = QPushButton()
        self.lang_btn.setFixedSize(62, 32)
        self.lang_btn.setFocusPolicy(Qt.NoFocus)
        self.lang_btn.clicked.connect(self._toggle_language)

        lay.addWidget(self.time_lbl)
        lay.addStretch(1)
        lay.addWidget(self.net_lbl)
        lay.addWidget(self.gw_lbl)
        lay.addWidget(self.auto_lbl)
        lay.addWidget(self.lang_btn)

        # ===============================
        # TIME UPDATE
        # ===============================
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_time)
        self.timer.start(60_000)  # mỗi phút
        self._update_time()

        self._update_lang_icon()

    # ===============================
    # LANGUAGE
    # ===============================
    def _toggle_language(self):
        self.lang_service.toggle()
        self._update_lang_icon()
        self.window().rebuild_ui()

    def _update_lang_icon(self):
        if self.lang_service.current_lang() == "vi":
            self.lang_btn.setText("VN")
            self.lang_btn.setToolTip("Tiếng Việt")
        else:
            self.lang_btn.setText("US")
            self.lang_btn.setToolTip("English")

    # ===============================
    # TIME
    # ===============================
    def _update_time(self):
        self.time_lbl.setText(
            "⏰ " + datetime.now().strftime("%H:%M")
        )

    # ===============================
    # STATUS API
    # ===============================
    def set_gateway(self, ok: bool):
        self.gw_lbl.setText(self.tr("🔗 OK" if ok else "🔴 DOWN"))

    def set_auto(self, enabled: bool):
        self.auto_lbl.setText(self.tr("Auto") if enabled else "⚠️")

    def set_wifi(self, text: str):
        self.net_lbl.setText(f"📶 {text}")

