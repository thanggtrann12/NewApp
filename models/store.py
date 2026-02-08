import json
import os
from typing import List, Optional
from .node import Node


class NodeStore:
    def __init__(self, path="nodes.json"):
        self.path = path
        self.nodes: List[Node] = []
        self.load()

    # ==================================================
    def load(self):
        if not os.path.exists(self.path):
            self.nodes = []
            return

        with open(self.path, "r", encoding="utf-8") as f:
            raw = json.load(f)
            self.nodes = [Node.from_dict(x) for x in raw]

    # ==================================================
    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(
                [n.to_dict() for n in self.nodes],
                f,
                indent=2,
                ensure_ascii=False
            )

    # ==================================================
    def list(self) -> List[Node]:
        return list(self.nodes)

    def get(self, node_id: str) -> Optional[Node]:
        for n in self.nodes:
            if n.id == node_id:
                return n
        return None

    def get_by_mac(self, mac: str) -> Optional[Node]:
        for n in self.nodes:
            if n.mac == mac:
                return n
        return None

    # ==================================================
    def add_or_update_by_mac(self, node: Node) -> Node:
        for n in self.nodes:
            if n.mac == node.mac:
                n.name = node.name
                n.pumps = node.pumps
                n.pump_crop_map = node.pump_crop_map
                n.pump_mode = node.pump_mode
                n.auto_type = node.auto_type
                n.pump_schedule = node.pump_schedule
                self.save()
                return n

        self.nodes.append(node)
        self.save()
        return node

    # ==================================================
    def remove(self, node_id: str):
        self.nodes = [n for n in self.nodes if n.id != node_id]
        self.save()

    def has_mac(self, mac: str) -> bool:
        return any(n.mac == mac for n in self.nodes)