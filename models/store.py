import json
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
        matches = self.list_by_mac(mac)
        return matches[0] if matches else None

    def list_by_mac(self, mac: str) -> List[Node]:
        target = self._normalize_mac(mac)
        if not target:
            return []
        return [
            n for n in self.nodes
            if self._normalize_mac(n.mac) == target
        ]

    def add_or_update_by_mac(self, node: Node):
        node.mac = self._normalize_mac(getattr(node, "mac", ""))
        node.node_type = Node._normalize_node_type(
            getattr(node, "node_type", "")
        )
        existing = self.get_by_mac(node.mac)
        if existing:
            changed = False

            incoming_name = (getattr(node, "name", "") or "").strip()
            if incoming_name and incoming_name != existing.name:
                existing.name = incoming_name
                changed = True

            incoming_pumps = int(getattr(node, "pumps", 0) or 0)
            if incoming_pumps > 0 and existing.pumps != incoming_pumps:
                existing.pumps = incoming_pumps
                changed = True

            incoming_type = Node._normalize_node_type(
                getattr(node, "node_type", "")
            )
            if incoming_type and existing.node_type != incoming_type:
                existing.node_type = incoming_type
                changed = True

            if changed:
                self.save()
            return existing
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

    def has_mac(self, mac: str) -> bool:
        target = self._normalize_mac(mac)
        return any(self._normalize_mac(n.mac) == target for n in self.nodes)

    @staticmethod
    def _normalize_mac(mac: str) -> str:
        return (mac or "").strip().lower()