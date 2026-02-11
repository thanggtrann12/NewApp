import uuid
from typing import Dict, List
from models.schedule import PumpSchedule


class Node:
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.mac = ""
        self.name = ""
        self.pumps = 0

        # ===== CONFIG (SAVE) =====
        self.pump_crop_map: Dict[int, str] = {}
        self.pump_mode: Dict[int, str] = {}
        self.auto_type: Dict[int, str] = {}
        self.pump_schedule: Dict[int, List[PumpSchedule]] = {}

        # ===== RUNTIME (NOT SAVE) =====
        self.pump_state = {}
        self.next_schedule = {}
        self.auto_running = {}
        self.auto_reason = {}

    @staticmethod
    def new(name="ESP Node"):
        n = Node()
        n.name = name
        return n

    # ==================================================
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "mac": self.mac,
            "name": self.name,
            "pumps": self.pumps,
            "pump_crop_map": {str(k): v for k, v in self.pump_crop_map.items()},
            "pump_mode": {str(k): v for k, v in self.pump_mode.items()},
            "auto_type": {str(k): v for k, v in self.auto_type.items()},
            "pump_schedule": {
                str(k): [
                    {
                        "time": s.time,
                        "duration": s.duration,
                        "meta": {"days": s.days}
                    } for s in schedules
                ]
                for k, schedules in self.pump_schedule.items()
            }
        }

    # ==================================================
    @staticmethod
    def from_dict(d: dict):
        n = Node()
        n.id = d.get("id", n.id)
        n.mac = d.get("mac", "").lower()
        n.name = d.get("name", "")
        n.pumps = int(d.get("pumps", 0) or 0)

        n.pump_crop_map = {int(k): v for k, v in d.get("pump_crop_map", {}).items()}
        n.pump_mode = {int(k): v for k, v in d.get("pump_mode", {}).items()}
        n.auto_type = {int(k): v for k, v in d.get("auto_type", {}).items()}

        n.pump_schedule = {
            int(k): Node._normalize_schedule(v)
            for k, v in d.get("pump_schedule", {}).items()
        }

        return n

    # ==================================================
    @staticmethod
    def _normalize_schedule(raw) -> List[PumpSchedule]:
        schedules = []
        for sch in raw:
            if isinstance(sch, dict):
                schedules.append(
                    PumpSchedule(
                        time=sch.get("time"),
                        duration=int(sch.get("duration", 0)),
                        days=sch.get("meta", {}).get("days", [])
                    )
                )
        return schedules
