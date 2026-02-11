import serial
import threading
import time
from bus.events import PumpStateEvent, NodeDiscoveredEvent


class SerialTransport(threading.Thread):
    """
    Serial adapter – NO business logic
    """

    def __init__(self, store, port="/dev/serial0", baud=115200):
        super().__init__(daemon=True)
        self.store = store
        self.port = port
        self.baud = baud
        self.bus = None
        self.running = True
        self.ser = None

    # =========================
    def attach_bus(self, bus):
        self.bus = bus

    # =========================
    # COMMANDS
    # =========================
    def send_manual(self, node, pump_idx, cmd):
        if not self.ser:
            return
        msg = f"MANUAL_CMD mac={node.mac} pump={pump_idx+1} cmd={cmd}\n"
        self.ser.write(msg.encode())

    def send_auto(self, node, pump_idx, duration):
        self.send_manual(node, pump_idx, "ON")

    def get_node_list(self):
        if self.ser:
            self.ser.write(b"GET_NODE_LIST\n")

    # =========================
    def run(self):
        while self.running:
            try:
                with serial.Serial(self.port, self.baud, timeout=1) as ser:
                    self.ser = ser
                    if self.bus:
                        self.bus.gateway_online.emit(True)

                    while self.running:
                        line = ser.readline().decode(errors="ignore").strip()
                        if line:
                            self._parse(line)

            except Exception as e:
                print("[SERIAL ERROR]", e)
                if self.bus:
                    self.bus.gateway_online.emit(False)
                time.sleep(2)

    # =========================
    def _parse(self, line: str):
        if line.startswith("PUMP "):
            parts = dict(p.split("=") for p in line.replace("PUMP ", "").split())
            node = self.store.get_by_mac(parts.get("mac", "").lower())
            if not node:
                return

            evt = PumpStateEvent(
                node_id=node.id,
                pump_idx=int(parts["idx"]),
                state=parts["state"],
                next_schedule=None
            )
            self.bus.pump_state.emit(evt)

        if line.startswith("NODE_ITEM"):
            data = dict(p.split("=") for p in line.split(";") if "=" in p)
            evt = NodeDiscoveredEvent(
                uid=data.get("uid"),
                mac=data.get("mac"),
                pumps=int(data.get("pumps", 0))
            )
            self.bus.node_discovered.emit(evt)
