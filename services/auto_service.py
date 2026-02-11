from services.weather_service import WeatherService
from services.auto_irrigation_engine import AutoIrrigationEngine


class AutoService:
    """
    Auto RECOMMEND service
    """

    def __init__(self, store, bus, crop_registry):
        self.store = store
        self.bus = bus
        self.engine = AutoIrrigationEngine(crop_registry)
        self.weather = WeatherService(lat=10.8231, lon=106.6297)

    # ==================================================
    def run(self):
        weather = self.weather.get_today()

        for node in self.store.list():
            decisions = self.engine.compute(node, weather)
            node._last_auto_decision = decisions
            node._last_weather = weather

            for idx, d in decisions.items():
                if node.auto_type.get(idx) != "RECOMMEND":
                    continue

                if d["action"] == "RUN":
                    node.next_schedule[idx] = (
                        d["time"], d["duration"]
                    )
                    node.auto_reason[idx] = d["reason"]

                    self.bus.send_auto(node, idx, d["duration"])
                    self.engine.record_run(
                        node, idx, d["duration"]
                    )
                else:
                    node.next_schedule.pop(idx, None)
                    node.auto_reason[idx] = d["reason"]

        self.store.save()
