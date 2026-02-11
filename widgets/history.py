from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget,
    QTableWidgetItem, QLabel
)
from PyQt5.QtCore import Qt
from services.history_service import HistoryService


class HistoryPage(QWidget):
    def __init__(self, history: HistoryService, parent=None):
        super().__init__(parent)
        self.history = history
        layout = QVBoxLayout(self)

        title = QLabel("History")
        title.setObjectName("AppTitle")
        layout.addWidget(title)

        self.table = QTableWidget(0, 6)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setHorizontalHeaderLabels([
            "Time",
            "Node",
            "Pump",
            "Action",
            "Source",
            "Duration",
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
        self.table.setItem(row, 3, QTableWidgetItem(evt.action))
        self.table.setItem(row, 4, QTableWidgetItem(evt.source))
        self.table.setItem(
            row, 5,
            QTableWidgetItem(
                f"{evt.duration} min" if evt.duration else "-"
            )
        )
