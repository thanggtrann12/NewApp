from dataclasses import dataclass
from datetime import datetime


@dataclass
class HistoryEvent:
    ts: datetime
    node_id: str
    pump_idx: int
    action: str      # START / STOP
    source: str      # MANUAL / TIMER / RECOMMEND
    duration: int | None = None
    reason: str | None = None
