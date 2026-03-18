from PyQt5.QtCore import QObject, pyqtSignal
from bus.events import PumpStateEvent


class CentralBus(QObject):
    """
    Single source of truth for ALL app events & commands
    """

    # ========= EVENTS (emit only by bus) =========
    pump_state = pyqtSignal(object)      # PumpStateEvent
    node_discovered = pyqtSignal(object) # NodeDiscoveredEvent
    node_list = pyqtSignal(object)
    sensor_data = pyqtSignal(object)     # SensorDataEvent
    config_changed = pyqtSignal(str)     # node_id – emitted when pump config/schedule saved
    zones_changed = pyqtSignal()         # emitted when zone mapping list is changed

    # ========= STATUS =========
    gateway_online = pyqtSignal(bool)

    # ========= SYNC STATE (set by transport) =========
    is_synced = False

    def __init__(self, history=None, parent=None):
        super().__init__(parent)
        self.history = history
        self.transport = None   # Serial / MQTT / REST

    # ==================================================
    # TRANSPORT BINDING
    # ==================================================
    def bind_transport(self, transport):
        self.transport = transport
        transport.attach_bus(self)

    # ==================================================
    # COMMAND API (ONLY ENTRY)
    # ==================================================
    def send_manual(self, node_id: str, pump_idx: int, cmd: str):
        state = "ON" if str(cmd).upper() == "ON" else "OFF"

        if self.transport:
            self.transport.send_manual(node_id, pump_idx, state)

        # Emit an optimistic state update so downstream listeners
        # (UI/Firebase) sync immediately on user interaction.
        self.pump_state.emit(
            PumpStateEvent(
                node_id=node_id,
                pump_idx=int(pump_idx),
                state=state,
                next_schedule=None,
                reason="manual_command",
                description="Lệnh thủ công",
            )
        )

        if self.history:
            self.history.add(
                node_id=node_id,
                pump_idx=pump_idx,
                action="START" if state == "ON" else "STOP",
                source="MANUAL",
                duration=None
            )

    def send_auto(self, node, pump_idx, duration: int):
        print("CEN_BUS->TRANS: AUTO")
        node_id = node.id if hasattr(node, "id") else node
        if self.history:
            self.history.add(
                node_id=node_id,
                pump_idx=pump_idx,
                action="START",
                source="TIMER",
                duration=duration
            )
        if self.transport:
            self.transport.send_auto(node_id, pump_idx, duration)

        # Keep AUTO consistent with MANUAL: emit optimistic ON so
        # UI/Firebase can reflect state immediately.
        reason = "auto_command"
        if hasattr(node, "auto_reason"):
            reason = str(
                getattr(node, "auto_reason", {}).get(int(pump_idx), "")
                or "auto_command"
            ).strip()

        self.pump_state.emit(
            PumpStateEvent(
                node_id=node_id,
                pump_idx=int(pump_idx),
                state="ON",
                next_schedule=None,
                reason=reason,
                description="Lệnh tự động",
            )
        )

    def request_node_list(self):
        if self.transport:
            self.transport.get_node_list()

    def send_add_node(self, mac: str):
        if self.transport:
            print(f"[BUS] CONFIRM NODE mac={mac}")
            self.transport.send_add_node(mac)

    def notify_config_changed(self, node_id: str):
        if node_id:
            self.config_changed.emit(node_id)

    def notify_zones_changed(self):
        self.zones_changed.emit()