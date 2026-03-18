from datetime import datetime, timedelta


class AutoIrrigationEngine:
    """
    Auto SCHEDULE engine
    - Crop-aware (min/max minutes, times/day)
    - Sensor-aware (moisture/temp/humidity)
    - Weather-aware (rain, temperature, humidity)
    - Cooldown + daily quota aware
    """

    VERY_DRY_MOISTURE = 30.0
    DRY_MOISTURE = 45.0
    WET_MOISTURE = 70.0

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
            if node.pump_mode.get(idx, "AUTO") != "AUTO":
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

        water = crop.water or {}
        min_minutes = int(water.get("min_minutes", 5) or 5)
        max_minutes = int(water.get("max_minutes", 15) or 15)
        times_per_day = int(water.get("times_per_day", 1) or 1)
        times_per_day = max(1, times_per_day)

        readings = self._sensor_for_pump(node, idx)
        moisture = self._as_float(readings.get("moisture"))
        sensor_temp = self._as_float(
            readings.get("temperature", readings.get("temp"))
        )
        sensor_humi = self._as_float(
            readings.get("humidity", readings.get("humi"))
        )

        temp = sensor_temp if sensor_temp is not None else weather.get("temp_max", 25)
        humidity = sensor_humi if sensor_humi is not None else weather.get("humidity", 50)
        base_mid = (min_minutes + max_minutes) // 2
        base_hint = max(min_minutes, min(max_minutes, base_mid))
        duration_hint = max(self.MIN_RUN, min(self.MAX_RUN, base_hint))
        next_hint = self._recommend_time(
            now=now,
            water=water,
            times_per_day=times_per_day,
            moisture=moisture,
            temp=temp,
        )

        # ----- cooldown -----
        last = node.__dict__.get("_last_run_at", {}).get(idx)
        if last and now - last < timedelta(hours=self.COOLDOWN_HOURS):
            remain = self.COOLDOWN_HOURS - int(
                (now - last).total_seconds() / 3600
            )
            next_allowed = last + timedelta(hours=self.COOLDOWN_HOURS)
            return self._skip(
                f"cooldown {remain}h remaining",
                time=next_allowed.strftime("%H:%M"),
                duration=duration_hint,
            )

        # ----- weather gate -----
        rain_prob = weather.get("rain_prob", 0)
        rain_mm = weather.get("rain_mm", 0)

        if rain_prob >= 70 and moisture is None:
            return self._skip(
                f"rain_prob={rain_prob}% >= 70%",
                time=next_hint,
                duration=duration_hint,
            )

        if rain_mm >= 5 and moisture is None:
            return self._skip(
                f"rain_mm={rain_mm}mm >= 5mm",
                time=next_hint,
                duration=duration_hint,
            )

        if moisture is not None and moisture >= self.WET_MOISTURE:
            return self._skip(
                f"moisture={moisture:.1f}% already wet",
                time=next_hint,
                duration=duration_hint,
            )

        # ----- daily quota -----
        today = now.date()
        used = node.__dict__.get("_daily_used", {}).get((idx, today), 0)
        quota = max_minutes * times_per_day

        if used >= quota:
            first_slot = self._build_daily_slots(water, times_per_day)[0]
            return self._skip(
                f"daily quota reached ({used}/{quota} min)",
                time=self._to_hhmm(first_slot),
                duration=duration_hint,
            )

        # ----- duration calc -----
        base = (min_minutes + max_minutes) // 2

        reason = [f"crop={crop.name}"]

        if moisture is None:
            reason.append("sensor=no-moisture")
        elif moisture < self.VERY_DRY_MOISTURE:
            base += 2
            reason.append(f"very_dry({moisture:.1f}%)")
        elif moisture < self.DRY_MOISTURE:
            base += 1
            reason.append(f"dry({moisture:.1f}%)")
        elif moisture > 60:
            base -= 1
            reason.append(f"moist({moisture:.1f}%)")

        if temp >= 35:
            base += 2
            reason.append(f"hot({temp}°C)")
        elif temp <= 22:
            base -= 1
            reason.append(f"cool({temp}°C)")

        if humidity >= 85:
            base -= 1
            reason.append(f"humid({humidity}%)")

        if rain_prob >= 60 or rain_mm >= 3:
            base -= 1
            reason.append(f"rain-risk({rain_prob}%/{rain_mm}mm)")

        crop_clamped = max(min_minutes, min(max_minutes, base))
        duration = max(self.MIN_RUN, min(self.MAX_RUN, crop_clamped))
        target_time = self._recommend_time(
            now=now,
            water=water,
            times_per_day=times_per_day,
            moisture=moisture,
            temp=temp,
        )

        return {
            "action": "RUN",
            "time": target_time,
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
    def _skip(self, reason, time=None, duration=None):
        payload = {
            "action": "SKIP",
            "reason": reason
        }

        if time:
            payload["time"] = time

        if duration is not None:
            payload["duration"] = int(duration)

        return payload

    def _recommend_time(
        self,
        now: datetime,
        water: dict,
        times_per_day: int,
        moisture,
        temp,
    ) -> str:
        # If soil is very dry, schedule near-now rather than waiting.
        if moisture is not None and moisture < self.VERY_DRY_MOISTURE:
            urgent = now + timedelta(minutes=2)
            return urgent.strftime("%H:%M")

        slots = self._build_daily_slots(water, times_per_day)

        # On hot days, move schedule earlier by 1 hour.
        if temp is not None and temp >= 34:
            slots = [((s - 60) % (24 * 60)) for s in slots]
            slots.sort()

        now_min = now.hour * 60 + now.minute
        for slot in slots:
            if slot >= now_min:
                return self._to_hhmm(slot)

        # No slot left today -> next day first slot.
        return self._to_hhmm(slots[0])

    def _build_daily_slots(self, water: dict, times_per_day: int):
        base = self._base_minutes_for_crop(water)
        interval = max(1, (24 * 60) // times_per_day)

        slots = []
        for i in range(times_per_day):
            slots.append((base + i * interval) % (24 * 60))

        slots = sorted(set(slots))
        return slots or [base]

    def _base_minutes_for_crop(self, water: dict) -> int:
        hhmm = (water or {}).get("base_time", "06:00")
        try:
            hh, mm = hhmm.split(":", 1)
            return int(hh) * 60 + int(mm)
        except (TypeError, ValueError):
            return 6 * 60

    @staticmethod
    def _to_hhmm(minutes: int) -> str:
        m = minutes % (24 * 60)
        hh = m // 60
        mm = m % 60
        return f"{hh:02d}:{mm:02d}"

    @staticmethod
    def _as_float(value):
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _sensor_for_pump(node, idx) -> dict:
        readings = getattr(node, "sensor_readings", {})
        if not isinstance(readings, dict):
            return {}
        raw = readings.get(idx, {})
        return raw if isinstance(raw, dict) else {}
