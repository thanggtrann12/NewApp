import random


class AutoIrrigationEngine:
    """
    Crop + Weather based AUTO irrigation engine

    - Stateless
    - Explainable
    - Safe
    """

    DEFAULT_TIME = "18:00"

    MAX_SINGLE_RUN = 15
    MIN_SINGLE_RUN = 3

    def __init__(self, crop_registry):
        self.crops = crop_registry

    # ==================================================
    def compute(self, node, weather: dict) -> dict:
        decisions = {}

        for idx in range(node.pumps):
            if node.pump_mode.get(idx) != "AUTO":
                continue

            crop_id = node.pump_crop_map.get(idx)
            decisions[idx] = self._decide_for_pump(
                crop_id, weather
            )

        return decisions

    # ==================================================
    def _decide_for_pump(self, crop_id: str | None, weather: dict) -> dict:
        # ❌ No crop
        if not crop_id:
            return {
                "action": "SKIP",
                "reason": "No crop set"
            }

        crop = self.crops.get(crop_id)
        if not crop:
            return {
                "action": "SKIP",
                "reason": "Unknown crop"
            }

        rain_prob = weather.get("rain_prob", 0)
        rain_mm = weather.get("rain_mm", 0)
        temp = weather.get("temp_max", 25)
        humidity = weather.get("humidity", 50)

        # 🌧️ HARD RAIN OVERRIDE
        if rain_prob >= 60 or rain_mm >= 3:
            return {
                "action": "SKIP",
                "reason": f"Rain expected ({rain_prob}%)"
            }

        w = crop.water

        # 🌱 BASE FROM CROP (CORE)
        base = random.randint(
            w["min_minutes"],
            w["max_minutes"]
        )
        reason = f"By crop: {crop.name}"

        # 🔥 TEMP ADJUST
        if temp >= 35:
            base += 2
            reason += f", hot ({temp}°C)"
        elif temp <= 22:
            base -= 1
            reason += f", cool ({temp}°C)"

        # 💧 HUMIDITY ADJUST
        if humidity >= 85:
            base -= 2
            reason += ", humid"

        # 🔒 SAFETY CLAMP
        duration = max(self.MIN_SINGLE_RUN, base)
        duration = min(self.MAX_SINGLE_RUN, duration)

        return {
            "action": "RUN",
            "time": self.DEFAULT_TIME,
            "duration": duration,
            "reason": reason
        }
