import serial
import threading
import time
from PyQt5.QtCore import QObject, pyqtSignal

from dialogs.discover_node_dialog import DiscoveredNode


# ==================================================
# SERIAL BUS
# ==================================================
class SerialNodeBus(QObject):
    nodeSnapshot = pyqtSignal(list)
    pumpStateChanged = pyqtSignal(str, int, str, object)

    def __init__(self, store=None):
        super().__init__()
        self.ser = None
        self.store = store
        self.is_synced = False

    # ------------------------------
    def bind_serial(self, ser):
        self.ser = ser

    # ------------------------------
    # SYNC
    # ------------------------------
    def request_sync(self):
        if not self.ser:
            return
        cmd = "SYNC_STATE\n"
        print("[PI → ESP32]", cmd.strip())
        self.ser.write(cmd.encode())

    # ------------------------------
    # COMMANDS → ESP32
    # ------------------------------
    def get_node_list(self):
        if not self.ser:
            return
        cmd = "GET_NODE_LIST\n"
        print("[PI → ESP32]", cmd.strip())
        self.ser.write(cmd.encode())

    def send_add_node(self, mac: str):
        if not self.ser:
            print("[BUS] serial not ready")
            return

        cmd = f"ADD_NODE mac={mac}\n"
        print("[PI → ESP32]", cmd.strip())
        self.ser.write(cmd.encode())

    def send_manual_command(self, node_id, pump_idx, cmd):
        if not self.ser or not self.store:
            return

        node = self.store.get(node_id)
        if not node:
            return

        msg = (
            f"MANUAL_CMD "
            f"mac={node.mac} "
            f"pump={pump_idx + 1} "
            f"cmd={cmd}\n"
        )
        print("[PI → ESP32]", msg.strip())
        self.ser.write(msg.encode())

    def send_auto_command(self, node_id, pump_idx, duration):
        print(
            f"[AUTO → BUS] Node={node_id} "
            f"Pump={pump_idx+1} {duration}min"
        )
        self.send_manual_command(node_id, pump_idx, "ON")


# ==================================================
# SERIAL LISTENER
# ==================================================
class SerialListener(threading.Thread):
    def __init__(self, bus, store, port="/dev/serial0", baud=115200):
        super().__init__(daemon=True)
        self.bus = bus
        self.store = store
        self.port = port
        self.baud = baud
        self.running = True

        # ===== STATE PARSE =====
        self._parsing_state = False
        self._current_node = None

        # ===== NODE LIST =====
        self._snapshot_active = False
        self._temp_nodes = {}

    # ==================================================
    def run(self):
        while self.running:
            try:
                with serial.Serial(self.port, self.baud, timeout=1) as ser:
                    print("[SERIAL] connected")
                    self.bus.bind_serial(ser)

                    # 🔥 request sync immediately
                    # self.bus.request_sync()

                    while self.running:
                        raw = ser.readline()
                        if not raw:
                            continue

                        line = raw.decode(
                            "utf-8", errors="ignore"
                        ).strip()

                        if not line:
                            continue

                        print("[UART]", line)
                        self._parse_line(line)

            except Exception as e:
                print("[SERIAL] error:", e)
                time.sleep(2)

    # ==================================================
    def _parse_line(self, line: str):
        # ===== STATE SNAPSHOT =====
        if line == "STATE_BEGIN":
            self._parsing_state = True
            self._current_node = None
            self.bus.is_synced = False
            return

        if line == "STATE_END":
            self._parsing_state = False
            self._current_node = None
            self.bus.is_synced = True
            print("[BUS] STATE SYNCED")
            return

        if self._parsing_state:
            self._parse_state_line(line)
            return

        # ===== NODE LIST =====
        if line == "NODE_LIST_BEGIN":
            self._snapshot_active = True
            self._temp_nodes = {}
            return

        if line == "NODE_LIST_END":
            self._snapshot_active = False
            self.bus.nodeSnapshot.emit(
                list(self._temp_nodes.values())
            )
            return

        if self._snapshot_active and line.startswith("NODE_ITEM:"):
            dn = self._parse_node_item(line)
            if dn.mac:
                self._temp_nodes[dn.mac] = dn
            return
        if line == "ESP_READY":
            print("[BUS] ESP reboot detected → clear UI state")

            for node in self.store.list():
                node.pump_state = {}
                node.next_schedule = {}

                for idx in range(node.pumps):
                    self.bus.pumpStateChanged.emit(
                        node.id,
                        idx,
                        "OFF",
                        None
                    )

            self.bus.is_synced = False
            return
    # ==================================================
    def _parse_state_line(self, line: str):
        # NODE mac=AA:BB:CC:DD:EE:FF pumps=4
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

            self.bus.pumpStateChanged.emit(self._current_node.id, idx, state, None)

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

        return DiscoveredNode(
            uid=data.get("uid", "ESP Node"),
            mac=data.get("mac", ""),
            pumps=int(data.get("pumps", 0))
        )
