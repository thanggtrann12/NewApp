from datetime import datetime, timedelta


class AutoIrrigationEngine:
    """
    Enterprise-grade AUTO irrigation engine
    - Deterministic
    - Explainable
    - Cooldown + daily quota aware
    """

    DEFAULT_TIME = "18:00"
    MIN_RUN = 3
    MAX_RUN = 15
    COOLDOWN_HOURS = 6

    def __init__(self, crop_registry):
        self.crops = crop_registry

    # ==================================================
    def compute(self, node, weather: dict) -> dict:
        decisions = {}
        now = datetime.now()

        for idx in range(node.pumps):
            if node.pump_mode.get(idx) != "AUTO":
                continue

            crop_id = node.pump_crop_map.get(idx)
            decisions[idx] = self._decide(
                node, idx, crop_id, weather, now
            )

        return decisions

    # ==================================================
    def _decide(self, node, idx, crop_id, weather, now):
        # ----- sanity -----
        if not crop_id:
            return self._skip("no crop")

        crop = self.crops.get(crop_id)
        if not crop:
            return self._skip("unknown crop")

        # ----- cooldown -----
        last = node.__dict__.get("_last_run_at", {}).get(idx)
        if last and now - last < timedelta(hours=self.COOLDOWN_HOURS):
            remain = self.COOLDOWN_HOURS - int(
                (now - last).total_seconds() / 3600
            )
            return self._skip(
                f"cooldown {remain}h remaining"
            )

        # ----- weather gate -----
        rain_prob = weather.get("rain_prob", 0)
        rain_mm = weather.get("rain_mm", 0)

        if rain_prob >= 60:
            return self._skip(
                f"rain_prob={rain_prob}% ≥ 60%"
            )

        if rain_mm >= 3:
            return self._skip(
                f"rain_mm={rain_mm}mm ≥ 3mm"
            )

        # ----- daily quota -----
        today = now.date()
        used = node.__dict__.get("_daily_used", {}).get((idx, today), 0)
        quota = crop.water.get("max_minutes", 15)

        if used >= quota:
            return self._skip(
                f"daily quota reached ({used}/{quota} min)"
            )

        # ----- duration calc -----
        base = (
            crop.water.get("min_minutes", 5) +
            crop.water.get("max_minutes", 15)
        ) // 2

        temp = weather.get("temp_max", 25)
        humidity = weather.get("humidity", 50)

        reason = [f"crop={crop.name}"]

        if temp >= 35:
            base += 2
            reason.append(f"hot({temp}°C)")
        elif temp <= 22:
            base -= 1
            reason.append(f"cool({temp}°C)")

        if humidity >= 85:
            base -= 1
            reason.append(f"humid({humidity}%)")

        duration = max(self.MIN_RUN, min(self.MAX_RUN, base))

        return {
            "action": "RUN",
            "time": self.DEFAULT_TIME,
            "duration": duration,
            "reason": ", ".join(reason)
        }

    # ==================================================
    def record_run(self, node, idx, duration):
        now = datetime.now()
        node.__dict__.setdefault("_last_run_at", {})[idx] = now

        key = (idx, now.date())
        node.__dict__.setdefault("_daily_used", {})
        node.__dict__["_daily_used"][key] = (
            node.__dict__["_daily_used"].get(key, 0) + duration
        )

    # ==================================================
    def _skip(self, reason):
        return {
            "action": "SKIP",
            "reason": reason
        }
