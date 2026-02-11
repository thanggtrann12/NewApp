import json
import os
from typing import List, Optional
from models.node import Node


class NodeStore:
    def __init__(self, path="nodes.json"):
        self.path = path
        self.nodes: List[Node] = []
        self.load()

    # ==================================================
    def load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            raw = []

        self.nodes = []
        for item in raw:
            from models.node import Node
            self.nodes.append(Node.from_dict(item))

    # ==================================================
    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(
                [n.to_dict() for n in self.nodes],
                f,
                indent=2,
                ensure_ascii=False
            )

    def list(self) -> List[Node]:
        return list(self.nodes)

    def get(self, node_id: str) -> Optional[Node]:
        return next((n for n in self.nodes if n.id == node_id), None)

    def get_by_mac(self, mac: str) -> Optional[Node]:
        return next((n for n in self.nodes if n.mac == mac), None)

    def add_or_update_by_mac(self, node: Node):
        for n in self.nodes:
            if n.mac == node.mac:
                return n
        self.nodes.append(node)
        self.save()
        return node

    def remove(self, node_id: str):
        """
        Remove node by id
        """
        before = len(self.nodes)
        self.nodes = [n for n in self.nodes if n.id != node_id]

        if len(self.nodes) != before:
            self.save()
