import uuid
from typing import List, Optional


class Zone:
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.name = ""

        # Physical mapping (phase 1)
        self.sensor_node_id = ""
        self.pump_node_id = ""
        # Legacy field kept for backward compatibility with old saved zones.
        self.sensor_indices: List[int] = []
        self.pump_idx: Optional[int] = None

        # Runtime-only cache for latest sensor values
        self.sensor_cache: dict = {}

    @staticmethod
    def new(name: str = "Zone"):
        z = Zone()
        z.name = name
        return z

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "sensor_node_id": self.sensor_node_id,
            "pump_node_id": self.pump_node_id,
            "sensor_indices": list(self.sensor_indices),
            "pump_idx": self.pump_idx,
        }

    @staticmethod
    def from_dict(d: dict):
        z = Zone()
        z.id = d.get("id", z.id)
        z.name = d.get("name", "")

        # Backward-compatible migration from legacy field `node_id`.
        legacy_node_id = d.get("node_id", "")
        z.sensor_node_id = d.get("sensor_node_id", legacy_node_id) or ""
        z.pump_node_id = d.get("pump_node_id", legacy_node_id) or ""

        z.sensor_indices = Zone._normalize_indices(
            d.get("sensor_indices", [])
        )

        raw_pump_idx = d.get("pump_idx", None)
        if raw_pump_idx is None or raw_pump_idx == "":
            z.pump_idx = None
        else:
            try:
                z.pump_idx = int(raw_pump_idx)
            except (TypeError, ValueError):
                z.pump_idx = None

        return z

    @staticmethod
    def _normalize_indices(raw) -> List[int]:
        indices: List[int] = []
        for item in raw or []:
            try:
                idx = int(item)
            except (TypeError, ValueError):
                continue
            if idx < 0:
                continue
            if idx not in indices:
                indices.append(idx)
        indices.sort()
        return indices
