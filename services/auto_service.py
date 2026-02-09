from services.weather_service import WeatherService
from services.auto_irrigation_engine import AutoIrrigationEngine


class AutoService:
    def __init__(self, bus, store):
        self.bus = bus
        self.store = store

        self.weather = WeatherService(
            lat=10.8231,
            lon=106.6297
        )
        self.engine = AutoIrrigationEngine()

    # ==================================================
    def run(self):
        weather = self.weather.get_today()

        for node in self.store.list():

            # ensure runtime fields
            if not hasattr(node, "next_schedule"):
                node.next_schedule = {}
            if not hasattr(node, "auto_reason"):
                node.auto_reason = {}

            # ===== HANDLE TIMER AUTO =====
            for idx, auto_type in node.auto_type.items():
                if auto_type == "TIMER":
                    schedules = node.pump_schedule.get(idx, [])
                    if schedules:
                        # take first schedule (or compute next if you want)
                        for sch in schedules:
                            t = sch["time"]
                            d = sch["duration"]

                        node.next_schedule[idx] = (t, d)
                        node.auto_reason[idx] = "Timer schedule"

                        # 🔥 notify UI
                        self.bus.pumpStateChanged.emit(
                            node.id,
                            idx,
                            node.pump_state.get(idx, "OFF"),
                            node.next_schedule[idx]
                        )

            # ===== HANDLE WEATHER AUTO =====
            decisions = self.engine.compute(node, weather)

            for idx, d in decisions.items():
                if d["action"] == "RUN":
                    node.next_schedule[idx] = (d["time"], d["duration"])
                    node.auto_reason[idx] = d["reason"]

                    self.bus.send_auto_command(
                        node.id, idx, d["duration"]
                    )
                else:
                    node.next_schedule.pop(idx, None)
                    node.auto_reason[idx] = d["reason"]

                # notify UI
                self.bus.pumpStateChanged.emit(
                    node.id,
                    idx,
                    node.pump_state.get(idx, "OFF"),
                    node.next_schedule.get(idx)
                )
