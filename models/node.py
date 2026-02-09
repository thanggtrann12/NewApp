import uuid


class Node:
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.mac = ""
        self.name = ""
        self.pumps = 0

        # ===== CONFIG (SAVE) =====
        self.pump_crop_map = {}
        self.pump_mode = {}
        self.auto_type = {}
        self.pump_schedule = {}

        # ===== RUNTIME (NOT SAVE) =====
        self.pump_state = {}
        self.next_schedule = {}
        self.auto_running = {}

    @staticmethod
    def new(name="ESP Node"):
        n = Node()
        n.name = name
        return n

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "mac": self.mac,
            "name": self.name,
            "pumps": self.pumps,
            "pump_crop_map": {str(k): v for k, v in self.pump_crop_map.items()},
            "pump_mode": {str(k): v for k, v in self.pump_mode.items()},
            "auto_type": {str(k): v for k, v in self.auto_type.items()},
            "pump_schedule": {str(k): v for k, v in self.pump_schedule.items()},
        }

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

    @staticmethod
    def _normalize_schedule(schedules):
        """
        Always return list[dict]
        """
        out = []
        for sch in schedules:
            # already dict
            if isinstance(sch, dict):
                out.append({
                    "time": sch.get("time"),
                    "duration": sch.get("duration"),
                    "meta": sch.get("meta", {})
                })

            # old list/tuple format
            elif isinstance(sch, (list, tuple)):
                out.append({
                    "time": sch[0],
                    "duration": sch[1],
                    "meta": {
                        "days": sch[2] if len(sch) > 2 else []
                    }
                })
        return out