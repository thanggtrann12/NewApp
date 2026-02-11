from PyQt5.QtCore import QObject, pyqtSignal


class CentralBus(QObject):
    """
    Single source of truth for ALL app events & commands
    """

    # ========= EVENTS (emit only by bus) =========
    pump_state = pyqtSignal(object)      # PumpStateEvent
    node_discovered = pyqtSignal(object) # NodeDiscoveredEvent
    node_list = pyqtSignal(object)

    # ========= STATUS =========
    gateway_online = pyqtSignal(bool)

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
        self.transport.send_manual(node_id, pump_idx, cmd)

        if self.history:
            self.history.add(
                node_id=node_id,
                pump_idx=pump_idx,
                action="START" if cmd == "ON" else "STOP",
                source="MANUAL",
                duration=None
            )

    def send_auto(self, node, pump_idx, duration: int):
        print("CEN_BUS->TRANS: AUTO")
        if self.history:
            self.history.add(
                node_id=node.id,
                pump_idx=pump_idx,
                action="START",
                source="TIMER",
                duration=duration
            )
        if self.transport:
            self.transport.send_auto(node, pump_idx, duration)

    def request_node_list(self):
        if self.transport:
            self.transport.get_node_list()

    def send_add_node(self, mac: str):
        if self.transport:
            print(f"[BUS] CONFIRM NODE mac={mac}")
            self.transport.send_add_node(mac)