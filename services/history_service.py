from PyQt5.QtCore import QObject, pyqtSignal
from datetime import datetime
from models.history import HistoryEvent


class HistoryService(QObject):
    eventAdded = pyqtSignal(HistoryEvent)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._events: list[HistoryEvent] = []

    def add(
        self,
        node_id: str,
        pump_idx: int,
        action: str,
        source: str,
        duration: int | None = None,
        reason: str | None = None,
    ):
        evt = HistoryEvent(
            ts=datetime.now(),
            node_id=node_id,
            pump_idx=pump_idx,
            action=action,
            source=source,
            duration=duration,
            reason=reason,
        )
        self._events.append(evt)
        self.eventAdded.emit(evt)

    def list(self) -> list[HistoryEvent]:
        return list(self._events)
