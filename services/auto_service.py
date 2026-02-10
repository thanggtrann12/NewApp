from services.weather_service import WeatherService
from services.auto_irrigation_engine import AutoIrrigationEngine


class AutoService:
    def __init__(self, bus, store, crop_registry):
        self.bus = bus
        self.store = store
        self.crops = crop_registry

        self.weather = WeatherService(lat=10.8231, lon=106.6297)
        self.engine = AutoIrrigationEngine(self.crops)

    # ==================================================
    def run(self):
        weather = self.weather.get_today()

        for node in self.store.list():

            if not hasattr(node, "next_schedule"):
                node.next_schedule = {}
            if not hasattr(node, "auto_reason"):
                node.auto_reason = {}

            # ===== AUTO TIMER =====
            for idx, auto_type in node.auto_type.items():
                if auto_type != "TIMER":
                    continue

                schedules = node.pump_schedule.get(idx, [])
                if not schedules:
                    continue

                sch = schedules[0]
                t = sch["time"]
                d = sch["duration"]

                node.next_schedule[idx] = (t, d)
                node.auto_reason[idx] = "Timer schedule"

                self.bus.pumpStateChanged.emit(
                    node.id,
                    idx,
                    node.pump_state.get(idx, "OFF"),
                    node.next_schedule[idx]
                )

            # ===== AUTO RECOMMEND (BY CROP + WEATHER) =====
            decisions = self.engine.compute(node, weather)
            node._last_auto_decision = decisions
            node._last_weather = weather
            for idx, d in decisions.items():
                auto_type = node.auto_type.get(idx)
                if auto_type != "RECOMMEND":
                    continue   # 🔥 KHÔNG đè TIMER

                if d["action"] == "RUN":
                    node.next_schedule[idx] = (d["time"], d["duration"])
                    node.auto_reason[idx] = d["reason"]

                    self.bus.send_auto_command(
                        node.id, idx, d["duration"]
                    )
                else:
                    node.next_schedule.pop(idx, None)
                    node.auto_reason[idx] = d["reason"]

                self.bus.pumpStateChanged.emit(
                    node.id,
                    idx,
                    node.pump_state.get(idx, "OFF"),
                    node.next_schedule.get(idx)
                )

        self.store.save()

