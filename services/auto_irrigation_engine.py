from datetime import datetime


class AutoIrrigationEngine:
    """
    Weather-based AUTO irrigation engine (no sensors)

    - Stateless
    - Safe
    - Explainable
    """

    # ===== SAFETY LIMITS =====
    MAX_SINGLE_RUN = 15        # minutes
    MIN_SINGLE_RUN = 3
    DEFAULT_TIME = "18:00"     # watering time

    # Crop water needs multiplier
    CROP_FACTOR = {
        "grass": 1.0,
        "flower": 0.7,
        "tree": 0.5,
        "vegetable": 0.9
    }

    def compute(self, node, weather: dict) -> dict:
        """
        Compute AUTO decision for all pumps in a node
        """
        decisions = {}

        for idx in range(node.pumps):
            if node.pump_mode.get(idx) != "AUTO":
                continue

            crop = getattr(node, "pump_crop_map", {}).get(idx, "grass")
            decisions[idx] = self._decide_for_pump(idx, crop, weather)

        return decisions

    # ==================================================
    def _decide_for_pump(self, idx: int, crop: str, weather: dict) -> dict:
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

        # 🔥 BASE DURATION FROM TEMPERATURE
        if temp >= 38:
            duration = 15
            reason = f"Very hot day ({temp}°C)"
        elif temp >= 33:
            duration = 12
            reason = f"Hot day ({temp}°C)"
        elif temp >= 28:
            duration = 8
            reason = f"Warm day ({temp}°C)"
        else:
            duration = 5
            reason = f"Cool day ({temp}°C)"

        # 💧 HUMIDITY ADJUST
        if humidity >= 85:
            duration -= 3
            reason += ", high humidity"

        # 🌱 CROP ADJUST
        factor = self.CROP_FACTOR.get(crop, 1.0)
        duration = int(duration * factor)

        # 🔒 SAFETY CLAMPS
        duration = max(self.MIN_SINGLE_RUN, duration)
        duration = min(self.MAX_SINGLE_RUN, duration)

        return {
            "action": "RUN",
            "time": self.DEFAULT_TIME,
            "duration": duration,
            "reason": reason
        }
