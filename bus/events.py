from dataclasses import dataclass
from typing import Optional


@dataclass
class PumpStateEvent:
    node_id: str
    pump_idx: int
    state: str
    next_schedule: Optional[tuple]


@dataclass
class NodeDiscoveredEvent:
    uid: str
    mac: str
    pumps: int
