import serial
import threading
import time
from bus.events import PumpStateEvent, NodeDiscoveredEvent, SensorDataEvent


class SerialTransport(threading.Thread):
    """
    Serial adapter – protocol parsing only
    NO business logic
    """

    def __init__(self, store, port="COM9", baud=115200):
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

                    # Fetch latest node identity snapshot (uid/name, mac, pumps)
                    # so UI can display real names from firmware.
                    self.get_node_list()

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

        # ===== LIVE SENSOR EVENT (always parse) =====
        # Handle SENSOR even during STATE snapshot so sensor stream is never dropped.
        if line.startswith("SENSOR "):
            self._handle_sensor_line(line)
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
            self._sync_nodes_from_snapshot(list(self._temp_nodes.values()))
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
                        evt = PumpStateEvent(
                            node_id=node.id,
                            pump_idx=idx,
                            state="OFF",
                            next_schedule=None
                        )
                        self.bus.pump_state.emit(evt)

            if self.bus:
                self.bus.is_synced = False
            return

        # ===== LIVE PUMP EVENT =====
        if line.startswith("PUMP "):
            parts = self._parse_kv(line.replace("PUMP ", ""))
            mac = parts.get("mac", "").lower()
            nodes = self.store.list_by_mac(mac)
            if not nodes:
                return

            if len(nodes) > 1:
                print(f"[SERIAL] duplicate mac={mac} -> fanout {len(nodes)} nodes")

            pump_idx = int(parts.get("idx", 0))
            state = parts.get("state", "OFF")
            serial_name = self._extract_serial_name(parts)
            for node in nodes:
                if serial_name:
                    node.name = serial_name
                evt = PumpStateEvent(
                    node_id=node.id,
                    pump_idx=pump_idx,
                    state=state,
                    next_schedule=None
                )
                self.bus.pump_state.emit(evt)
            return

    def _handle_sensor_line(self, line: str):
        # Legacy protocol:
        #   SENSOR mac=AA:BB:CC idx=0 type=moisture val=72.5
        # New packed protocol:
        #   SENSOR mac=AA:BB:CC moisture=72 temp=27.50 humidity=61.00
        parts = self._parse_kv(line.replace("SENSOR ", ""))
        mac_raw = parts.get("mac", "")
        if not mac_raw:
            return

        nodes = self.store.list_by_mac(mac_raw)
        if not nodes:
            print(f"[SERIAL] SENSOR ignored: unknown mac={mac_raw}")
            return

        if len(nodes) > 1:
            print(f"[SERIAL] duplicate mac={mac_raw} -> fanout {len(nodes)} nodes")

        idx = self._safe_int(parts.get("idx", 0), 0)
        node_type = self._extract_node_type(parts)
        serial_name = self._sanitize_name_for_type(
            self._extract_serial_name(parts),
            node_type,
        )
        readings = {}

        if "type" in parts and "val" in parts:
            # Backward compatibility with old line-per-sensor format.
            stype = self._normalize_sensor_key(parts.get("type", ""))
            val = self._safe_float(parts.get("val"))
            if stype and val is not None:
                readings[stype] = val
        else:
            # New packed format from firmware.
            moisture = self._safe_float(parts.get("moisture"))
            temperature = self._safe_float(
                parts.get("temperature", parts.get("temp"))
            )
            humidity = self._safe_float(
                parts.get("humidity", parts.get("humi"))
            )

            if moisture is not None:
                readings["moisture"] = moisture
            if temperature is not None:
                readings["temperature"] = temperature
            if humidity is not None:
                readings["humidity"] = humidity

        if not readings:
            return

        identity_changed = False
        for node in nodes:
            can_apply_identity = self._node_type_compatible(
                node,
                node_type,
            )

            if can_apply_identity and serial_name and node.name != serial_name:
                node.name = serial_name
                identity_changed = True

            if can_apply_identity and node_type and node.node_type != node_type:
                node.node_type = node_type
                identity_changed = True

            if idx not in node.sensor_readings:
                node.sensor_readings[idx] = {}
            node.sensor_readings[idx].update(readings)

            if self.bus:
                evt = SensorDataEvent(
                    node_id=node.id,
                    pump_idx=idx,
                    readings=dict(node.sensor_readings[idx])
                )
                self.bus.sensor_data.emit(evt)

        if identity_changed:
            self.store.save()

    # ==================================================
    def _parse_state_line(self, line: str):
        # NODE mac=AA:BB:CC pumps=4
        if line.startswith("NODE "):
            parts = self._parse_kv(line.replace("NODE ", ""))
            mac = parts.get("mac", "").lower()
            pumps = int(parts.get("pumps", 0))
            serial_name = self._extract_serial_name(parts)

            node = self.store.get_by_mac(mac)
            if not node:
                return

            node.pumps = pumps
            if serial_name:
                node.name = serial_name
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
                evt = PumpStateEvent(
                    node_id=self._current_node.id,
                    pump_idx=idx,
                    state=state,
                    next_schedule=None
                )
                self.bus.pump_state.emit(evt)

    # ==================================================
    def _parse_kv(self, text: str) -> dict:
        data = {}
        for p in text.split():
            if "=" in p:
                k, v = p.split("=", 1)
                data[k] = v
        return data

    @staticmethod
    def _safe_int(value, default=0):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _safe_float(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _normalize_sensor_key(key: str) -> str:
        k = (key or "").strip().lower()
        if k in ("moisture", "soil", "soil_moisture"):
            return "moisture"
        if k in ("temperature", "temp"):
            return "temperature"
        if k in ("humidity", "humi"):
            return "humidity"
        return ""

    # ==================================================
    def _parse_node_item(self, line: str):
        body = line[len("NODE_ITEM:"):]
        data = {}

        if ";" in body:
            for p in body.split(";"):
                if "=" in p:
                    k, v = p.split("=", 1)
                    data[k.strip()] = v.strip()
        else:
            data = self._parse_kv(body)

        uid = (
            data.get("uid")
            or data.get("name")
            or data.get("node")
            or "ESP Node"
        )

        node_type = self._extract_node_type(data)
        pumps = int(data.get("pumps", 0) or 0)
        if not node_type:
            node_type = "pump_node" if pumps > 0 else "sensor_node"

        return NodeDiscoveredEvent(
            uid=uid,
            mac=data.get("mac", ""),
            pumps=pumps,
            node_type=node_type,
        )

    def _sync_nodes_from_snapshot(self, discovered_nodes: list):
        changed = False

        for dn in discovered_nodes:
            nodes = self.store.list_by_mac(getattr(dn, "mac", ""))
            if not nodes:
                continue

            pumps = int(getattr(dn, "pumps", 0) or 0)
            node_type = self._normalize_node_type(
                getattr(dn, "node_type", "")
            )
            name = self._sanitize_name_for_type(
                (getattr(dn, "uid", "") or "").strip(),
                node_type,
            )

            for node in nodes:
                can_apply_identity = self._node_type_compatible(
                    node,
                    node_type,
                )

                if can_apply_identity and name and node.name != name:
                    node.name = name
                    changed = True
                if pumps > 0 and node.pumps != pumps:
                    node.pumps = pumps
                    changed = True
                if can_apply_identity and node_type and node.node_type != node_type:
                    node.node_type = node_type
                    changed = True

        if changed:
            self.store.save()

    @staticmethod
    def _extract_serial_name(parts: dict) -> str:
        name = (
            (parts or {}).get("uid")
            or (parts or {}).get("name")
            or (parts or {}).get("node")
            or ""
        )
        return str(name).strip()

    @classmethod
    def _extract_node_type(cls, parts: dict) -> str:
        raw = (
            (parts or {}).get("node_type")
            or (parts or {}).get("device_type")
            or (parts or {}).get("role")
            or (parts or {}).get("kind")
            or (parts or {}).get("type")
            or ""
        )
        return cls._normalize_node_type(raw)

    @staticmethod
    def _normalize_node_type(value: str) -> str:
        v = (value or "").strip().lower()
        if v in ("sensor_node", "sensor", "sensornode"):
            return "sensor_node"
        if v in (
            "pump_node",
            "pump",
            "pumpnode",
            "relay_node",
            "actuator_node",
        ):
            return "pump_node"
        return ""

    @classmethod
    def _node_type_compatible(cls, node, incoming_type: str) -> bool:
        incoming = cls._normalize_node_type(incoming_type)
        if not incoming:
            return True
        current = cls._normalize_node_type(
            getattr(node, "node_type", "")
        )
        if not current:
            return True
        return current == incoming

    @classmethod
    def _sanitize_name_for_type(cls, name: str, node_type: str) -> str:
        text = str(name or "").strip()
        if not text:
            return ""
        kind = cls._normalize_node_type(node_type)
        lower = text.lower()
        if kind == "pump_node" and lower.startswith("sensor"):
            return ""
        if kind == "sensor_node" and lower.startswith("pump"):
            return ""
        return text
