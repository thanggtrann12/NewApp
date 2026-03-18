import json
from typing import List, Optional
from models.zone import Zone


class ZoneStore:
    def __init__(self, path="zones.json"):
        self.path = path
        self.zones: List[Zone] = []
        self.load()

    def load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            raw = []

        self.zones = [Zone.from_dict(item) for item in raw]

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(
                [z.to_dict() for z in self.zones],
                f,
                indent=2,
                ensure_ascii=False,
            )

    def list(self) -> List[Zone]:
        return list(self.zones)

    def get(self, zone_id: str) -> Optional[Zone]:
        return next((z for z in self.zones if z.id == zone_id), None)

    def add(self, zone: Zone):
        self.zones.append(zone)
        self.save()
        return zone

    def remove(self, zone_id: str):
        before = len(self.zones)
        self.zones = [z for z in self.zones if z.id != zone_id]
        if len(self.zones) != before:
            self.save()
