# models/node.py
from dataclasses import dataclass
import uuid
from typing import Dict

@dataclass
class Node:
    id: str
    crops: int = 1
    mac: str = ""
    name: str = ""  # tùy chọn, để sau nếu cần đặt tên node

    @staticmethod
    def new(crops: int = 1, mac: str = "", name: str = "") -> "Node":
        return Node(id=str(uuid.uuid4()), crops=crops, mac=mac, name=name)

    def to_dict(self) -> Dict:
        return {"id": self.id, "crops": self.crops, "mac": self.mac, "name": self.name}

    @staticmethod
    def from_dict(d: Dict) -> "Node":
        return Node(
            id=d["id"],
            crops=int(d.get("crops", 1)),
            mac=d.get("mac", ""),
            name=d.get("name", ""),
        )