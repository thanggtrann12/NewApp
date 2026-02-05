# models/store.py
import json
import os
from typing import List, Optional
from .node import Node

class NodeStore:
    def __init__(self, path: str = "nodes.json"):
        self.path = path
        self.nodes: List[Node] = []
        self.load()

    def load(self):
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.nodes = [Node.from_dict(x) for x in data]
        else:
            self.nodes = []

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump([n.to_dict() for n in self.nodes], f, ensure_ascii=False, indent=2)

    # CRUD
    def list(self) -> List[Node]:
        return list(self.nodes)

    def add(self, node: Node):
        self.nodes.append(node)
        self.save()

    def remove(self, node_id: str):
        self.nodes = [n for n in self.nodes if n.id != node_id]
        self.save()

    def get(self, node_id: str) -> Optional[Node]:
        for n in self.nodes:
            if n.id == node_id:
                return n
        return None

    def update(self, node: Node):
        for i, n in enumerate(self.nodes):
            if n.id == node.id:
                self.nodes[i] = node
                self.save()
                return