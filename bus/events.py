from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PumpStateEvent:
    node_id: str
    pump_idx: int
    state: str
    next_schedule: Optional[tuple] = None
    reason: str = ""
    description: str = ""


@dataclass
class NodeDiscoveredEvent:
    uid: str
    mac: str
    pumps: int
    node_type: str = ""


@dataclass
class SensorDataEvent:
    """Emitted every time a SENSOR line arrives from a node."""
    node_id: str
    pump_idx: int
    readings: dict = field(default_factory=dict)
    # e.g. {"moisture": 72.0, "temperature": 25.3, "humidity": 60.0}
