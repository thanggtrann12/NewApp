from datetime import datetime
import threading
import time

from services.weather_service import WeatherService
from services.auto_irrigation_engine import AutoIrrigationEngine


class AutoService:
    """
    Auto RECOMMEND service
    """

    # Immediate ON is only allowed below this moisture threshold.
    IMMEDIATE_MOISTURE_THRESHOLD = AutoIrrigationEngine.VERY_DRY_MOISTURE
    # Stop immediate run when moisture recovers to wet zone.
    IMMEDIATE_STOP_MOISTURE_THRESHOLD = AutoIrrigationEngine.WET_MOISTURE
    # Re-arm window to avoid duplicate ON bursts from dense sensor packets.
    IMMEDIATE_REARM_SEC = 45
    # Keep pump ON for a short minimum window before recovery-based stop.
    IMMEDIATE_MIN_RUN_SEC = 20
    # Require N consecutive wet samples before stopping immediate run.
    IMMEDIATE_WET_CONFIRM_COUNT = 2

    def __init__(self, store, bus, crop_registry, zone_store=None):
        self.store = store
        self.bus = bus
        self.zone_store = zone_store
        self.engine = AutoIrrigationEngine(crop_registry)
        self.weather = WeatherService(lat=10.8231, lon=106.6297)
        self._last_sensor_recompute_ts = 0.0
        self._sensor_recompute_cooldown_sec = 15
        self._last_immediate_trigger_ts = {}
        self._immediate_running = {}
        self._immediate_stop_timers = {}
        self._immediate_lock = threading.Lock()
        self._wet_recovery_streak = {}

        if hasattr(self.bus, "sensor_data"):
            self.bus.sensor_data.connect(self._on_sensor_data)
        if hasattr(self.bus, "config_changed"):
            self.bus.config_changed.connect(
                self._on_config_refresh_requested
            )
        if hasattr(self.bus, "node_list"):
            self.bus.node_list.connect(
                self._on_config_refresh_requested
            )

    # ==================================================
    def run(self, dispatch_commands: bool = False, persist: bool = True):
        weather = self.weather.get_today()
        now = datetime.now()

        for node in self.store.list():
            decisions = self.engine.compute(node, weather)
            node._last_auto_decision = decisions
            node._last_weather = weather

            for idx, d in decisions.items():
                auto_type = node.auto_type.get(idx, "SCHEDULE")
                if auto_type == "RECOMMEND":
                    auto_type = "SCHEDULE"
                    node.auto_type[idx] = auto_type

                if auto_type != "SCHEDULE":
                    continue

                if d["action"] == "RUN":
                    node.next_schedule[idx] = (
                        d["time"], d["duration"]
                    )
                    node.auto_reason[idx] = d["reason"]

                    if (
                        dispatch_commands
                        and self._is_due_now(d.get("time"), now)
                    ):
                        self.bus.send_auto(node, idx, d["duration"])
                        self.engine.record_run(
                            node, idx, d["duration"]
                        )
                else:
                    next_time = d.get("time")
                    next_duration = self._safe_int(
                        d.get("duration", 0),
                        0,
                    )
                    if next_time:
                        if next_duration <= 0:
                            prev = node.next_schedule.get(idx)
                            if (
                                isinstance(prev, (tuple, list))
                                and len(prev) >= 2
                            ):
                                next_duration = self._safe_int(prev[1], 1)
                            else:
                                next_duration = 1

                        node.next_schedule[idx] = (
                            next_time,
                            max(1, next_duration),
                        )
                    else:
                        node.next_schedule.pop(idx, None)

                    node.auto_reason[idx] = d["reason"]

        if persist:
            self.store.save()

    def _on_sensor_data(self, evt):
        self._mirror_sensor_to_pump_nodes(evt)
        self._stop_immediate_if_recovered(evt)
        self._dispatch_immediate_if_very_dry(evt)

        # Recompute recommended schedule from latest sensor data,
        # but never trigger pump command from this path.
        now_ts = time.time()
        if now_ts - self._last_sensor_recompute_ts < self._sensor_recompute_cooldown_sec:
            return

        self._last_sensor_recompute_ts = now_ts
        try:
            self.run(dispatch_commands=False, persist=False)
        except Exception as e:
            print(f"[AutoService] recompute from sensor failed: {e}")

    def _on_config_refresh_requested(self, *_):
        # Recompute preview immediately after config updates
        # (local dialog save or remote Firebase change).
        try:
            self.run(dispatch_commands=False, persist=False)
        except Exception as e:
            print(f"[AutoService] recompute from config failed: {e}")

    def _dispatch_immediate_if_very_dry(self, evt):
        moisture = self._extract_moisture(getattr(evt, "readings", {}))
        if moisture is None or moisture >= self.IMMEDIATE_MOISTURE_THRESHOLD:
            return

        # Reset wet confirmation streak when moisture is dry again.
        self._wet_recovery_streak[evt.node_id] = 0

        targets = self._targets_for_sensor(evt.node_id)
        if not targets:
            return

        weather = self.weather.get_today()
        now_ts = time.time()
        decision_cache = {}
        triggered = False

        for node, pump_idx in targets:
            if node.pump_mode.get(pump_idx, "AUTO") != "AUTO":
                continue

            auto_type = self._normalize_auto_type(
                node.auto_type.get(pump_idx, "SCHEDULE")
            )
            if auto_type != "SCHEDULE":
                continue

            node.pump_state = getattr(node, "pump_state", {})
            if node.pump_state.get(pump_idx) == "ON":
                continue

            key = (node.id, pump_idx)

            with self._immediate_lock:
                if key in self._immediate_running:
                    continue

            last_ts = self._last_immediate_trigger_ts.get(key, 0.0)
            if now_ts - last_ts < self.IMMEDIATE_REARM_SEC:
                continue

            if node.id not in decision_cache:
                decision_cache[node.id] = self.engine.compute(node, weather)

            decision = decision_cache[node.id].get(pump_idx)
            if not decision:
                continue

            action = decision.get("action")
            override_cooldown = (
                action != "RUN"
                and self._can_override_cooldown_for_immediate(decision)
            )
            if action != "RUN" and not override_cooldown:
                continue

            duration = int(decision.get("duration", 0) or 0)
            if duration <= 0:
                continue

            reason = decision.get("reason", "")
            if override_cooldown:
                reason = (
                    f"{reason}, cooldown-override"
                    if reason
                    else "cooldown-override"
                )

            node.auto_reason = getattr(node, "auto_reason", {})
            node.auto_reason[pump_idx] = (
                f"{reason}, immediate-dry({moisture:.1f}%)"
                if reason
                else f"immediate-dry({moisture:.1f}%)"
            )

            self.bus.send_auto(node, pump_idx, duration)
            self.engine.record_run(node, pump_idx, duration)

            node.pump_state[pump_idx] = "ON"
            node.next_schedule[pump_idx] = (
                datetime.now().strftime("%H:%M"),
                duration,
            )

            self._last_immediate_trigger_ts[key] = now_ts
            with self._immediate_lock:
                self._immediate_running[key] = {
                    "started_ts": now_ts,
                    "duration_sec": duration * 60,
                }
            self._schedule_immediate_timeout_stop(
                node.id,
                pump_idx,
                duration * 60,
            )
            triggered = True

        if triggered:
            print(
                "[AutoService] immediate run triggered "
                f"for very dry moisture={moisture:.1f}%"
            )

    def _stop_immediate_if_recovered(self, evt):
        moisture = self._extract_moisture(getattr(evt, "readings", {}))
        if moisture is None:
            return
        if moisture < self.IMMEDIATE_STOP_MOISTURE_THRESHOLD:
            self._wet_recovery_streak[evt.node_id] = 0
            return

        streak = self._wet_recovery_streak.get(evt.node_id, 0) + 1
        self._wet_recovery_streak[evt.node_id] = streak
        if streak < self.IMMEDIATE_WET_CONFIRM_COUNT:
            return

        now_ts = time.time()
        for node, pump_idx in self._targets_for_sensor(evt.node_id):
            key = (node.id, pump_idx)
            with self._immediate_lock:
                session = self._immediate_running.get(key)

            if not session:
                continue

            if now_ts - float(session.get("started_ts", 0.0)) < self.IMMEDIATE_MIN_RUN_SEC:
                continue

            self._stop_immediate_session(
                node.id,
                pump_idx,
                reason=f"recovered({moisture:.1f}%)",
            )

    def _schedule_immediate_timeout_stop(
        self,
        node_id: str,
        pump_idx: int,
        duration_sec: int,
    ):
        key = (node_id, pump_idx)
        self._cancel_immediate_timer(key)

        timer = threading.Timer(
            max(1, int(duration_sec)),
            self._stop_immediate_session,
            args=(node_id, pump_idx, "timeout"),
        )
        timer.daemon = True

        with self._immediate_lock:
            self._immediate_stop_timers[key] = timer

        timer.start()

    def _cancel_immediate_timer(self, key):
        timer = None
        with self._immediate_lock:
            timer = self._immediate_stop_timers.pop(key, None)

        if timer:
            timer.cancel()

    def _stop_immediate_session(self, node_id: str, pump_idx: int, reason: str):
        key = (node_id, pump_idx)
        self._cancel_immediate_timer(key)

        with self._immediate_lock:
            session = self._immediate_running.pop(key, None)

        if not session:
            return

        node = self.store.get(node_id)
        if not node:
            return

        node.pump_state = getattr(node, "pump_state", {})
        is_on = node.pump_state.get(pump_idx) == "ON"
        node.pump_state[pump_idx] = "OFF"
        node.next_schedule.pop(pump_idx, None)

        prev = node.auto_reason.get(pump_idx, "")
        tail = f"immediate-stop:{reason}"
        node.auto_reason[pump_idx] = f"{prev}, {tail}" if prev else tail

        if is_on:
            self.bus.send_manual(node_id, pump_idx, "OFF")

        print(
            "[AutoService] immediate run stopped "
            f"node={node_id} pump={pump_idx+1} reason={reason}"
        )

        # Recompute next schedule immediately after stop so UI always
        # has an up-to-date "next watering" time.
        try:
            self.run(dispatch_commands=False, persist=False)
        except Exception as e:
            print(f"[AutoService] immediate stop recompute failed: {e}")

    def _mirror_sensor_to_pump_nodes(self, evt):
        if not self.zone_store:
            return

        for zone in self.zone_store.list():
            if zone.sensor_node_id != evt.node_id:
                continue

            if not zone.pump_node_id or zone.pump_idx is None:
                continue

            pump_node = self.store.get(zone.pump_node_id)
            if not pump_node:
                continue

            pump_node.sensor_readings = getattr(pump_node, "sensor_readings", {})
            pump_node.sensor_readings[zone.pump_idx] = dict(evt.readings or {})

    def _targets_for_sensor(self, sensor_node_id: str):
        if not self.zone_store:
            return []

        targets = []
        seen = set()
        for zone in self.zone_store.list():
            if zone.sensor_node_id != sensor_node_id:
                continue
            if not zone.pump_node_id or zone.pump_idx is None:
                continue

            try:
                pump_idx = int(zone.pump_idx)
            except (TypeError, ValueError):
                continue

            key = (zone.pump_node_id, pump_idx)
            if key in seen:
                continue

            node = self.store.get(zone.pump_node_id)
            if not node:
                continue

            seen.add(key)
            targets.append((node, pump_idx))

        return targets

    @staticmethod
    def _extract_moisture(readings: dict):
        try:
            return float((readings or {}).get("moisture"))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _safe_int(value, default=0):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _normalize_auto_type(value: str) -> str:
        if value == "RECOMMEND":
            return "SCHEDULE"
        if value in ("SCHEDULE", "TIMER"):
            return value
        return "SCHEDULE"

    @staticmethod
    def _can_override_cooldown_for_immediate(decision: dict) -> bool:
        reason = str((decision or {}).get("reason", "") or "").strip().lower()
        return reason.startswith("cooldown")

    @staticmethod
    def _is_due_now(target_time: str, now: datetime, tolerance_sec: int = 60) -> bool:
        if not target_time:
            return False
        try:
            hh, mm = target_time.split(":", 1)
            target = now.replace(
                hour=int(hh),
                minute=int(mm),
                second=0,
                microsecond=0,
            )
        except (ValueError, TypeError):
            return False

        return abs((now - target).total_seconds()) <= tolerance_sec
