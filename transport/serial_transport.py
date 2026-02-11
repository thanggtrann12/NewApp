import serial
import threading
import time
from bus.events import PumpStateEvent, NodeDiscoveredEvent


class SerialTransport(threading.Thread):
    """
    Serial adapter – protocol parsing only
    NO business logic
    """

    def __init__(self, store, port="/dev/serial0", baud=115200):
        super().__init__(daemon=True)
        self.store = store
        self.port = port
        self.baud = baud

        self.bus = None
        self.running = True
        self.ser = None

        # ===== snapshot / state parsing =====
        self._parsing_state = False
        self._current_node = None

        self._snapshot_active = False
        self._temp_nodes = {}

    # ==================================================
    def attach_bus(self, bus):
        self.bus = bus

    # ==================================================
    # COMMANDS
    # ==================================================
    def send_manual(self, node_id: str, pump_idx: int, cmd: str):
        node = self.store.get(node_id)
        if not node:
            print(f"[SERIAL] node not found: {node_id}")
            return

        if not self.ser:
            print("[SERIAL] not connected")
            return

        msg = (
            f"MANUAL_CMD mac={node.mac} pump={pump_idx + 1} cmd={cmd}\n"
        )
        self.ser.write(msg.encode())

    def send_auto(self, node_id: str, pump_idx: int, duration: int):
        # AUTO is still MANUAL ON at protocol level
        self.send_manual(node_id, pump_idx, "ON")

    def get_node_list(self):
        if self.ser:
            self.ser.write(b"GET_NODE_LIST\n")

    def send_add_node(self, mac: str):
        if not self.ser:
            print("[SERIAL] not connected")
            return

        cmd = f"ADD_NODE mac={mac}\n"
        print("[PI → ESP32]", cmd.strip())
        self.ser.write(cmd.encode())
        
    # ==================================================
    # THREAD LOOP
    # ==================================================
    def run(self):
        while self.running:
            try:
                with serial.Serial(self.port, self.baud, timeout=1) as ser:
                    self.ser = ser
                    print("[SERIAL] connected")

                    if self.bus:
                        self.bus.gateway_online.emit(True)

                    while self.running:
                        line = ser.readline().decode(
                            errors="ignore"
                        ).strip()
                        if line:
                            self._parse_line(line)

            except Exception as e:
                print("[SERIAL ERROR]", e)
                self.ser = None
                if self.bus:
                    self.bus.gateway_online.emit(False)
                time.sleep(2)

    # ==================================================
    # PROTOCOL PARSER
    # ==================================================
    def _parse_line(self, line: str):
        print(line)
        # ===== STATE SNAPSHOT =====
        if line == "STATE_BEGIN":
            self._parsing_state = True
            self._current_node = None
            if self.bus:
                self.bus.is_synced = False
            return

        if line == "STATE_END":
            self._parsing_state = False
            self._current_node = None
            if self.bus:
                self.bus.is_synced = True
            print("[BUS] STATE SYNCED")
            return

        if self._parsing_state:
            self._parse_state_line(line)
            return

        # ===== NODE LIST SNAPSHOT =====
        if line == "NODE_LIST_BEGIN":
            self._snapshot_active = True
            self._temp_nodes = {}
            return

        if line == "NODE_LIST_END":
            self._snapshot_active = False
            if self.bus:
                self.bus.node_list.emit(
                    list(self._temp_nodes.values())
                )
            return

        if self._snapshot_active and line.startswith("NODE_ITEM:"):
            dn = self._parse_node_item(line)
            if dn.mac:
                self._temp_nodes[dn.mac] = dn
            return

        # ===== ESP REBOOT =====
        if line == "ESP_READY":
            print("[BUS] ESP reboot detected → clear UI state")

            for node in self.store.list():
                node.pump_state = {}
                node.next_schedule = {}

                for idx in range(node.pumps):
                    if self.bus:
                        self.bus.pump_state.emit(
                            node.id,
                            idx,
                            "OFF",
                            None
                        )

            if self.bus:
                self.bus.is_synced = False
            return

        # ===== LIVE PUMP EVENT =====
        if line.startswith("PUMP "):
            parts = self._parse_kv(line.replace("PUMP ", ""))
            mac = parts.get("mac", "").lower()
            node = self.store.get_by_mac(mac)
            if not node:
                return

            evt = PumpStateEvent(
                node_id=node.id,
                pump_idx=int(parts.get("idx", 0)),
                state=parts.get("state", "OFF"),
                next_schedule=None
            )
            self.bus.pump_state.emit(evt)

    # ==================================================
    def _parse_state_line(self, line: str):
        # NODE mac=AA:BB:CC pumps=4
        if line.startswith("NODE "):
            parts = self._parse_kv(line.replace("NODE ", ""))
            mac = parts.get("mac", "").lower()
            pumps = int(parts.get("pumps", 0))

            node = self.store.get_by_mac(mac)
            if not node:
                return

            node.pumps = pumps
            node.pump_state = {}
            self._current_node = node
            return

        # PUMP idx=0 state=ON
        if line.startswith("PUMP ") and self._current_node:
            parts = self._parse_kv(line.replace("PUMP ", ""))
            idx = int(parts.get("idx", 0))
            state = parts.get("state", "OFF")

            self._current_node.pump_state[idx] = state

            if self.bus:
                self.bus.pump_state.emit(
                    self._current_node.id,
                    idx,
                    state,
                    None
                )

    # ==================================================
    def _parse_kv(self, text: str) -> dict:
        data = {}
        for p in text.split():
            if "=" in p:
                k, v = p.split("=", 1)
                data[k] = v
        return data

    # ==================================================
    def _parse_node_item(self, line: str):
        body = line[len("NODE_ITEM:"):]
        data = {}

        for p in body.split(";"):
            if "=" in p:
                k, v = p.split("=", 1)
                data[k] = v

        return NodeDiscoveredEvent(
            uid=data.get("uid", "ESP Node"),
            mac=data.get("mac", ""),
            pumps=int(data.get("pumps", 0))
        )
