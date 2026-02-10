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

        self.setWindowTitle(self.tr("Auto Decision Debug"))
        self.setModal(True)
        self.setMinimumWidth(360)

        root = QVBoxLayout(self)
        root.setSpacing(12)

        # =========================
        # BASIC INFO
        # =========================
        info_box = QGroupBox(self.tr("Pump Info"))
        info_lay = QFormLayout(info_box)

        info_lay.addRow(
            self.tr("Pump:"),
            QLabel(self.tr("Pump {n}").format(n=pump_idx + 1))
        )
        info_lay.addRow(
            self.tr("Crop:"),
            QLabel(crop.name if crop else self.tr("Not set"))
        )
        info_lay.addRow(
            self.tr("Mode:"),
            QLabel(node.auto_type.get(pump_idx, "RECOMMEND"))
        )

        root.addWidget(info_box)

        # =========================
        # WEATHER
        # =========================
        w_box = QGroupBox(self.tr("Weather"))
        w_lay = QFormLayout(w_box)

        w_lay.addRow(
            self.tr("Rain probability:"),
            QLabel(f"{weather.get('rain_prob', 0)} %")
        )
        w_lay.addRow(
            self.tr("Rain amount (mm):"),
            QLabel(f"{weather.get('rain_mm', 0)}")
        )
        w_lay.addRow(
            self.tr("Max temperature:"),
            QLabel(f"{weather.get('temp_max', '-')} °C")
        )
        w_lay.addRow(
            self.tr("Humidity:"),
            QLabel(f"{weather.get('humidity', '-')} %")
        )

        root.addWidget(w_box)

        # =========================
        # DECISION
        # =========================
        d_box = QGroupBox(self.tr("Decision"))
        d_lay = QFormLayout(d_box)

        d_lay.addRow(
            self.tr("Action:"),
            QLabel(decision.get("action", "-"))
        )

        if decision.get("action") == "RUN":
            d_lay.addRow(
                self.tr("Time:"),
                QLabel(decision.get("time", "-"))
            )
            d_lay.addRow(
                self.tr("Duration:"),
                QLabel(
                    self.tr("{min} min").format(
                        min=decision.get("duration", "-")
                    )
                )
            )

        d_lay.addRow(
            self.tr("Reason:"),
            QLabel(decision.get("reason", "-"))
        )

        root.addWidget(d_box)

        # =========================
        # FOOTER
        # =========================
        btn = QPushButton(self.tr("Close"))
        btn.setFixedHeight(36)
        btn.clicked.connect(self.accept)

        root.addWidget(btn, alignment=Qt.AlignRight)
