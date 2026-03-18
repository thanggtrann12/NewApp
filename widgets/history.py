from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget,
    QTableWidgetItem, QLabel
)
from services.history_service import HistoryService


class HistoryPage(QWidget):
    def __init__(self, history: HistoryService, parent=None):
        super().__init__(parent)
        self.history = history
        layout = QVBoxLayout(self)

        title = QLabel("Lịch sử")
        title.setObjectName("AppTitle")
        layout.addWidget(title)

        self.table = QTableWidget(0, 6)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setHorizontalHeaderLabels([
            "Thời gian",
            "Thiết bị",
            "Bơm",
            "Hành động",
            "Nguồn",
            "Thời lượng",
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        layout.addWidget(self.table)

        for evt in history.list():
            self._append(evt)

        history.eventAdded.connect(self._append)

    def _append(self, evt):
        row = self.table.rowCount()
        self.table.insertRow(row)

        self.table.setItem(
            row, 0,
            QTableWidgetItem(evt.ts.strftime("%H:%M:%S"))
        )
        self.table.setItem(row, 1, QTableWidgetItem(evt.node_id))
        self.table.setItem(row, 2, QTableWidgetItem(str(evt.pump_idx + 1)))
        self.table.setItem(row, 3, QTableWidgetItem(self._action_text(evt.action)))
        self.table.setItem(row, 4, QTableWidgetItem(self._source_text(evt.source)))
        self.table.setItem(
            row, 5,
            QTableWidgetItem(
                f"{evt.duration} phút" if evt.duration else "-"
            )
        )

    @staticmethod
    def _action_text(action: str) -> str:
        value = str(action or "").strip().upper()
        if value == "ON":
            return "BẬT"
        if value == "OFF":
            return "TẮT"
        return str(action or "")

    @staticmethod
    def _source_text(source: str) -> str:
        value = str(source or "").strip().lower()
        mapping = {
            "manual": "Thủ công",
            "auto": "Tự động",
            "timer": "Hẹn giờ",
            "schedule": "Lịch",
            "serial": "Serial",
            "firebase": "Firebase",
        }
        return mapping.get(value, str(source or ""))
