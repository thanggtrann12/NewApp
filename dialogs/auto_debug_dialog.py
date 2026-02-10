from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout,
    QLabel, QPushButton, QGroupBox
)
from PyQt5.QtCore import Qt


class AutoDebugDialog(QDialog):
    def __init__(
        self,
        node,
        pump_idx: int,
        crop,
        weather: dict,
        decision: dict,
        parent=None
    ):
        super().__init__(parent)

        self.setWindowTitle("Auto Decision Debug")
        self.setModal(True)
        self.setMinimumWidth(360)

        root = QVBoxLayout(self)
        root.setSpacing(12)

        # =========================
        # BASIC INFO
        # =========================
        info_box = QGroupBox("Pump Info")
        info_lay = QFormLayout(info_box)

        info_lay.addRow("Pump:", QLabel(f"Pump {pump_idx + 1}"))
        info_lay.addRow("Crop:", QLabel(crop.name if crop else "Not set"))
        info_lay.addRow(
            "Mode:",
            QLabel(
                node.auto_type.get(pump_idx, "RECOMMEND")
            )
        )

        root.addWidget(info_box)

        # =========================
        # WEATHER
        # =========================
        w_box = QGroupBox("Weather")
        w_lay = QFormLayout(w_box)

        w_lay.addRow(
            "Rain prob:",
            QLabel(f"{weather.get('rain_prob', 0)} %")
        )
        w_lay.addRow(
            "Rain mm:",
            QLabel(f"{weather.get('rain_mm', 0)}")
        )
        w_lay.addRow(
            "Temp max:",
            QLabel(f"{weather.get('temp_max', '-')} °C")
        )
        w_lay.addRow(
            "Humidity:",
            QLabel(f"{weather.get('humidity', '-')} %")
        )

        root.addWidget(w_box)

        # =========================
        # DECISION
        # =========================
        d_box = QGroupBox("Decision")
        d_lay = QFormLayout(d_box)

        d_lay.addRow(
            "Action:",
            QLabel(decision.get("action", "-"))
        )

        if decision.get("action") == "RUN":
            d_lay.addRow(
                "Time:",
                QLabel(decision.get("time", "-"))
            )
            d_lay.addRow(
                "Duration:",
                QLabel(f"{decision.get('duration', '-')} min")
            )

        d_lay.addRow(
            "Reason:",
            QLabel(decision.get("reason", "-"))
        )

        root.addWidget(d_box)

        # =========================
        # FOOTER
        # =========================
        btn = QPushButton("Close")
        btn.setFixedHeight(36)
        btn.clicked.connect(self.accept)

        root.addWidget(btn, alignment=Qt.AlignRight)
