import logging
import threading
from datetime import datetime
from models.schedule import PumpSchedule

logger = logging.getLogger(__name__)


class FirebaseTransport:
    """
    Bidirectional Firebase Realtime Database bridge.

    PUSH  (Pi → Firebase):
      - sensor_data       → /nodes/{id}/sensor/{pump_idx}
      - pump_state        → /nodes/{id}/pump_state/{pump_idx}
      - node config       → /nodes/{id}/config   (startup + config_changed)

    PULL  (Firebase → Pi → Serial):
      - /commands/{id}/{pump_idx}  {"cmd": "ON"|"OFF", "ts": "..."}
        → bus.send_manual() → SerialTransport → ESP32
    """

    ROOT = "irrigation"

    def __init__(
        self,
        store,
        bus,
        credential_path: str,
        database_url: str,
        zone_store=None,
        crop_registry=None,
    ):
        self.store = store
        self.bus = bus
        self.zone_store = zone_store
        self.crop_registry = crop_registry
        self._db = None
        self._streams = []
        self._listening_command_node_ids = set()
        self._listening_config_node_ids = set()
        self._listening_zones = False
        self._suppress_zone_push = False
        self._lock = threading.Lock()
        self._init_firebase(credential_path, database_url)

    # ==================================================
    # INIT
    # ==================================================
    def _init_firebase(self, credential_path: str, database_url: str):
        try:
            import firebase_admin
            from firebase_admin import credentials, db

            cred = credentials.Certificate(credential_path)
            firebase_admin.initialize_app(cred, {"databaseURL": database_url})
            self._db = db
            logger.info("[FIREBASE] initialized OK")
        except Exception as e:
            logger.error(f"[FIREBASE] init failed: {e}")
            self._db = None

    # ==================================================
    # START / STOP
    # ==================================================
    def start(self):
        if not self._db:
            logger.warning("[FIREBASE] not available – skipping start")
            return False

        # ---- bus signal → Firebase push ----
        self.bus.sensor_data.connect(self._on_sensor_data)
        self.bus.pump_state.connect(self._on_pump_state)
        self.bus.config_changed.connect(self._on_config_changed)
        self.bus.node_list.connect(self._on_node_list)
        if hasattr(self.bus, "zones_changed"):
            self.bus.zones_changed.connect(self._on_zones_changed)

        # ---- push initial snapshots & start command listeners ----
        self._sync_known_nodes()
        self._push_zones()
        self._listen_remote_zones()

        logger.info("[FIREBASE] started – listening for remote commands")
        return True

    def stop(self):
        with self._lock:
            for stream in self._streams:
                try:
                    stream.close()
                except Exception:
                    pass
            self._streams.clear()
            self._listening_command_node_ids.clear()
            self._listening_config_node_ids.clear()
            self._listening_zones = False

    # ==================================================
    # PUSH: sensor data
    # ==================================================
    def _on_sensor_data(self, evt):
        if not self._db:
            return
        try:
            self._db.reference(
                f"{self.ROOT}/nodes/{evt.node_id}/sensor/{evt.pump_idx}"
            ).set({**evt.readings, "_ts": self._ts()})
        except Exception as e:
            logger.error(f"[FIREBASE] sensor push: {e}")

    # ==================================================
    # PUSH: pump state
    # ==================================================
    def _on_pump_state(self, evt):
        if not self._db:
            return
        try:
            reason, description = self._resolve_pump_reason(evt)
            self._db.reference(
                f"{self.ROOT}/nodes/{evt.node_id}/pump_state/{evt.pump_idx}"
            ).set({
                "state": evt.state,
                "reason": reason,
                "description": description,
                "_ts": self._ts(),
            })
        except Exception as e:
            logger.error(f"[FIREBASE] pump_state push: {e}")

    # ==================================================
    # PUSH: node config
    # ==================================================
    def _on_config_changed(self, node_id: str):
        node = self.store.get(node_id)
        if node:
            self._push_node_config(node)
            self._listen_commands(node)
            self._listen_remote_config(node)

    def _on_node_list(self, _nodes):
        # Serial snapshot may include newly registered nodes after startup.
        self._sync_known_nodes()

    def _on_zones_changed(self):
        if self._suppress_zone_push:
            return
        self._push_zones()

    def _listen_remote_zones(self):
        if not self._db or not self.zone_store or self._listening_zones:
            return

        try:
            ref = self._db.reference(f"{self.ROOT}/zones")

            def on_zones(event):
                payload = self._event_payload_dict(ref, event)
                event_path = str(getattr(event, "path", "/") or "/")
                event_data = getattr(event, "data", None)
                changed = self._apply_remote_zones(
                    payload,
                    event_path=event_path,
                    event_data=event_data,
                )
                if not changed:
                    return

                logger.info("[FIREBASE] remote zones applied")
                if self.bus and hasattr(self.bus, "zones_changed"):
                    self._suppress_zone_push = True
                    try:
                        self.bus.zones_changed.emit()
                    finally:
                        self._suppress_zone_push = False

            stream = ref.listen(on_zones)
            with self._lock:
                self._streams.append(stream)
                self._listening_zones = True

        except Exception as e:
            logger.error(f"[FIREBASE] listen_remote_zones: {e}")

    def _push_node_config(self, node):
        if not self._db:
            return
        try:
            pump_cfg = {}
            for i in range(node.pumps):
                schedules = node.pump_schedule.get(i, [])
                crop_id = node.pump_crop_map.get(i, "")
                crop_name = self._resolve_crop_name(crop_id)
                pump_cfg[str(i)] = {
                    "mode":      node.pump_mode.get(i, "AUTO"),
                    "auto_type": node.auto_type.get(i, "SCHEDULE"),
                    "crop_id":   crop_id,
                    "crop_name": crop_name,
                    "schedule": [self._schedule_to_dict(s) for s in schedules]
                }

            self._db.reference(f"{self.ROOT}/nodes/{node.id}/config").set({
                "name":        node.name,
                "mac":         node.mac,
                "pumps":       node.pumps,
                "pump_config": pump_cfg,
                "_updated":    self._ts()
            })
            logger.debug(f"[FIREBASE] config pushed: {node.id}")
        except Exception as e:
            logger.error(f"[FIREBASE] config push: {e}")

    def _resolve_crop_name(self, crop_id: str) -> str:
        if not crop_id or not self.crop_registry:
            return ""

        crop = self.crop_registry.get(crop_id)
        return str(getattr(crop, "name", "") or "")

    def _push_zones(self):
        if not self._db or not self.zone_store:
            return
        try:
            payload = {}
            for zone in self.zone_store.list():
                payload[zone.id] = {
                    "id": zone.id,
                    "name": zone.name,
                    "sensor_node_id": zone.sensor_node_id,
                    "pump_node_id": zone.pump_node_id,
                    "sensor_indices": list(zone.sensor_indices or []),
                    "pump_idx": zone.pump_idx,
                }

            self._db.reference(f"{self.ROOT}/zones").set(payload)
            self._db.reference(f"{self.ROOT}/zones_meta").set(
                {"updated_at": self._ts(), "count": len(payload)}
            )
        except Exception as e:
            logger.error(f"[FIREBASE] zones push: {e}")

    def _sync_known_nodes(self):
        for node in self.store.list():
            self._push_node_config(node)
            self._listen_commands(node)
            self._listen_remote_config(node)

    def sync_all_configs(self):
        """Force-sync all node configs to Firebase (e.g. after store rebuild)."""
        for node in self.store.list():
            self._push_node_config(node)

    # ==================================================
    # PULL: remote commands  (Firebase → Pi → Serial)
    # ==================================================
    def _listen_commands(self, node):
        """
        Listens to /commands/{node_id} for incoming pump commands.
        Phone app writes:
            /irrigation/commands/{node_id}/{pump_idx}
                = {"cmd": "ON", "ts": "2026-03-11T10:00:00"}
        Pi processes it → deletes the entry → sends via Serial.
        """
        if not self._db:
            return

        node_id = node.id
        if node_id in self._listening_command_node_ids:
            return

        try:
            ref = self._db.reference(f"{self.ROOT}/commands/{node_id}")

            def on_cmd(event):
                data = self._event_payload_dict(ref, event)
                if not data:
                    return

                consume_root = False
                if self._is_command_payload_dict(data):
                    # Support direct write at /commands/{node_id}
                    # without pump index nesting.
                    data = {"_root": data}
                    consume_root = True

                for pump_str, payload in data.items():
                    cmd, payload_pump_idx = self._parse_remote_command(payload)
                    if cmd not in ("ON", "OFF"):
                        continue

                    payload_reason = ""
                    if isinstance(payload, dict):
                        payload_reason = str(
                            payload.get("reason")
                            or payload.get("source")
                            or ""
                        ).strip()

                    pump_idx = self._safe_int(pump_str, -1)
                    if pump_idx < 0:
                        pump_idx = self._safe_int(payload_pump_idx, -1)
                    if pump_idx < 0:
                        pump_idx = 0

                    logger.info(
                        f"[FIREBASE] remote cmd "
                        f"node={node_id} pump={pump_idx} cmd={cmd}"
                    )

                    node = self.store.get(node_id)
                    if node:
                        node.auto_reason = getattr(node, "auto_reason", {})
                        node.auto_reason[pump_idx] = (
                            payload_reason or "manual_command"
                        )

                    # Route through CentralBus → SerialTransport → ESP32
                    self.bus.send_manual(node_id, pump_idx, cmd)

                    # Delete processed command
                    try:
                        if consume_root:
                            ref.delete()
                        else:
                            self._db.reference(
                                f"{self.ROOT}/commands/{node_id}/{pump_str}"
                            ).delete()
                    except Exception:
                        pass

            stream = ref.listen(on_cmd)
            with self._lock:
                self._streams.append(stream)
                self._listening_command_node_ids.add(node_id)

        except Exception as e:
            logger.error(f"[FIREBASE] listen_commands: {e}")

    def _listen_remote_config(self, node):
        if not self._db:
            return

        node_id = node.id
        if node_id in self._listening_config_node_ids:
            return

        try:
            ref = self._db.reference(f"{self.ROOT}/nodes/{node_id}/config")

            def on_cfg(event):
                data = self._event_payload_dict(ref, event)

                changed = self._apply_remote_node_config(node_id, data)
                if not changed:
                    return

                logger.info(f"[FIREBASE] remote config applied: {node_id}")
                if self.bus:
                    # Trigger card refresh in zone UI.
                    self.bus.node_list.emit(self.store.list())

            stream = ref.listen(on_cfg)
            with self._lock:
                self._streams.append(stream)
                self._listening_config_node_ids.add(node_id)

        except Exception as e:
            logger.error(f"[FIREBASE] listen_remote_config: {e}")

    def _apply_remote_node_config(self, node_id: str, payload: dict) -> bool:
        node = self.store.get(node_id)
        if not node:
            return False

        changed = False

        incoming_name = str(payload.get("name", "") or "").strip()
        if incoming_name and incoming_name != node.name:
            node.name = incoming_name
            changed = True

        incoming_pumps = self._safe_int(payload.get("pumps"), node.pumps)
        if incoming_pumps > 0 and incoming_pumps != node.pumps:
            node.pumps = incoming_pumps
            changed = True

        pump_cfg = payload.get("pump_config", {})
        if isinstance(pump_cfg, dict):
            for pump_key, cfg in pump_cfg.items():
                if not isinstance(cfg, dict):
                    continue

                idx = self._safe_int(pump_key, -1)
                if idx < 0:
                    continue

                incoming_mode = self._normalize_pump_mode(
                    cfg.get("mode", "AUTO")
                )
                if node.pump_mode.get(idx, "AUTO") != incoming_mode:
                    node.pump_mode[idx] = incoming_mode
                    changed = True

                incoming_auto_type = self._normalize_auto_type(
                    cfg.get("auto_type", "SCHEDULE")
                )
                if node.auto_type.get(idx, "SCHEDULE") != incoming_auto_type:
                    node.auto_type[idx] = incoming_auto_type
                    changed = True

                incoming_crop = str(cfg.get("crop_id", "") or "")
                if node.pump_crop_map.get(idx, "") != incoming_crop:
                    node.pump_crop_map[idx] = incoming_crop
                    changed = True

                incoming_schedules = self._normalize_remote_schedule(
                    cfg.get("schedule", [])
                )
                if not self._same_schedule(
                    node.pump_schedule.get(idx, []),
                    incoming_schedules,
                ):
                    node.pump_schedule[idx] = incoming_schedules
                    changed = True

        if changed:
            self.store.save()

        return changed

    def _apply_remote_zones(
        self,
        payload: dict,
        event_path: str = "/",
        event_data=None,
    ) -> bool:
        if not self.zone_store:
            return False

        from models.zone import Zone

        incoming = payload if isinstance(payload, dict) else {}
        current_zones = self.zone_store.list()
        current_ids = [str(z.id) for z in current_zones]
        current_map = {str(z.id): z.to_dict() for z in current_zones}

        is_root_event = event_path in ("", "/")
        if is_root_event and not incoming and current_zones:
            logger.warning(
                "[FIREBASE] ignore empty root zones payload "
                "to avoid destructive reset"
            )
            return False

        merged = {} if is_root_event else dict(current_map)

        # Handle single-zone deletion event: path like "/{zone_id}", data=None.
        if not is_root_event and event_data is None:
            parts = [p for p in event_path.split("/") if p]
            if len(parts) == 1:
                merged.pop(parts[0], None)

        for zone_id, raw in incoming.items():
            if raw is None:
                zid = str(zone_id or "").strip()
                if zid:
                    merged.pop(zid, None)
                continue

            if not isinstance(raw, dict):
                continue

            zid = str(
                raw.get("id")
                or raw.get("zone_id")
                or zone_id
                or ""
            ).strip()
            if not zid:
                continue

            base = dict(current_map.get(zid, merged.get(zid, {})))

            def pick(*keys, default=None):
                for key in keys:
                    if key in raw:
                        return raw.get(key)
                return default

            merged[zid] = {
                "id": zid,
                "name": str(
                    pick("name", default=base.get("name", "")) or ""
                ),
                "sensor_node_id": str(
                    pick(
                        "sensor_node_id",
                        "sensorNodeId",
                        "node_id",
                        default=base.get("sensor_node_id", ""),
                    ) or ""
                ),
                "pump_node_id": str(
                    pick(
                        "pump_node_id",
                        "pumpNodeId",
                        default=base.get("pump_node_id", ""),
                    ) or ""
                ),
                "sensor_indices": pick(
                    "sensor_indices",
                    "sensorIndices",
                    default=base.get("sensor_indices", []),
                ),
                "pump_idx": pick(
                    "pump_idx",
                    "pumpIdx",
                    default=base.get("pump_idx", None),
                ),
            }

        ordered_ids = [zid for zid in current_ids if zid in merged]
        ordered_ids.extend(
            [zid for zid in merged.keys() if zid not in current_ids]
        )

        new_zones = [Zone.from_dict(merged[zid]) for zid in ordered_ids]

        current_sig = [self._zone_signature(z) for z in current_zones]
        new_sig = [self._zone_signature(z) for z in new_zones]
        if current_sig == new_sig:
            return False

        self.zone_store.zones = new_zones
        self.zone_store.save()
        return True

    @staticmethod
    def _zone_signature(zone) -> tuple:
        return (
            str(getattr(zone, "id", "") or ""),
            str(getattr(zone, "name", "") or ""),
            str(getattr(zone, "sensor_node_id", "") or ""),
            str(getattr(zone, "pump_node_id", "") or ""),
            tuple(getattr(zone, "sensor_indices", []) or []),
            getattr(zone, "pump_idx", None),
        )

    def _event_payload_dict(self, ref, event) -> dict:
        data = getattr(event, "data", None)
        path = str(getattr(event, "path", "/") or "/")

        if path in ("", "/") and isinstance(data, dict):
            return data

        if isinstance(data, dict) and path.count("/") == 1:
            key = path.strip("/")
            if key:
                return {key: data}

        snapshot = self._read_ref_dict(ref)
        return snapshot if isinstance(snapshot, dict) else {}

    @staticmethod
    def _read_ref_dict(ref):
        try:
            value = ref.get()
            if isinstance(value, dict):
                return value
            if isinstance(value, list):
                return {
                    str(i): item
                    for i, item in enumerate(value)
                    if item is not None
                }
            return {}
        except Exception:
            return {}

    @staticmethod
    def _is_command_payload_dict(value) -> bool:
        if not isinstance(value, dict):
            return False
        return any(k in value for k in ("cmd", "action", "state"))

    @classmethod
    def _parse_remote_command(cls, payload):
        if isinstance(payload, dict):
            cmd = (
                payload.get("cmd")
                or payload.get("action")
                or payload.get("state")
            )
            pump_idx = (
                payload.get("pump_idx")
                or payload.get("pump")
                or payload.get("idx")
            )
        elif isinstance(payload, str):
            cmd = payload
            pump_idx = None
        else:
            return "", None

        normalized = str(cmd or "").strip().upper()
        if normalized not in ("ON", "OFF"):
            return "", pump_idx
        return normalized, pump_idx

    @staticmethod
    def _schedule_to_dict(schedule):
        if isinstance(schedule, dict):
            return {
                "time": schedule.get("time", ""),
                "duration": schedule.get("duration", 0),
                "days": schedule.get("days", []),
            }
        return {
            "time": getattr(schedule, "time", ""),
            "duration": getattr(schedule, "duration", 0),
            "days": getattr(schedule, "days", []),
        }

    @classmethod
    def _normalize_remote_schedule(cls, raw_list):
        normalized = []
        seen = set()

        for item in raw_list or []:
            if not isinstance(item, dict):
                continue

            hhmm = str(item.get("time", "") or "").strip()
            if not cls._is_hhmm(hhmm):
                continue

            duration = cls._safe_int(item.get("duration"), 0)
            if duration <= 0:
                continue

            raw_days = item.get("days", [])
            if isinstance(raw_days, dict):
                raw_days = raw_days.get("days", [])

            days = cls._normalize_days(raw_days)
            key = (hhmm, duration, tuple(days))
            if key in seen:
                continue

            seen.add(key)
            normalized.append(
                PumpSchedule(
                    time=hhmm,
                    duration=duration,
                    days=days,
                )
            )

        return normalized

    @classmethod
    def _same_schedule(cls, left, right) -> bool:
        return cls._schedule_signature(left) == cls._schedule_signature(right)

    @classmethod
    def _schedule_signature(cls, schedules):
        signature = []
        for sch in schedules or []:
            if isinstance(sch, dict):
                hhmm = str(sch.get("time", "") or "").strip()
                duration = cls._safe_int(sch.get("duration"), 0)
                raw_days = sch.get("days", [])
            else:
                hhmm = str(getattr(sch, "time", "") or "").strip()
                duration = cls._safe_int(getattr(sch, "duration", 0), 0)
                raw_days = getattr(sch, "days", [])

            days = tuple(cls._normalize_days(raw_days))
            signature.append((hhmm, duration, days))

        return signature

    @staticmethod
    def _safe_int(value, default=0):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _normalize_days(raw_days):
        days = []
        for d in raw_days or []:
            try:
                idx = int(d)
            except (TypeError, ValueError):
                continue
            if 0 <= idx <= 6 and idx not in days:
                days.append(idx)
        days.sort()
        return days

    @staticmethod
    def _is_hhmm(value: str) -> bool:
        if not value or ":" not in value:
            return False
        try:
            hh, mm = value.split(":", 1)
            hh_i = int(hh)
            mm_i = int(mm)
            return 0 <= hh_i <= 23 and 0 <= mm_i <= 59
        except (TypeError, ValueError):
            return False

    @staticmethod
    def _normalize_auto_type(value: str) -> str:
        if value == "RECOMMEND":
            return "SCHEDULE"
        if value in ("SCHEDULE", "TIMER"):
            return value
        return "SCHEDULE"

    @staticmethod
    def _normalize_pump_mode(value: str) -> str:
        if value == "MANUAL":
            return "AUTO"
        if value == "AUTO":
            return value
        return "AUTO"

    def _resolve_pump_reason(self, evt) -> tuple[str, str]:
        reason = str(getattr(evt, "reason", "") or "").strip().strip(",")
        description = str(getattr(evt, "description", "") or "").strip()

        if not reason:
            node = self.store.get(getattr(evt, "node_id", ""))
            if node:
                auto_reason = getattr(node, "auto_reason", {})
                reason = str(
                    auto_reason.get(getattr(evt, "pump_idx", -1), "") or ""
                ).strip().strip(",")

        if not reason:
            reason = "manual_command"

        if not description:
            description = self._reason_description(reason)

        return reason, description

    @staticmethod
    def _reason_description(reason: str) -> str:
        text = str(reason or "").strip().lower()
        if not text:
            return "Lệnh thủ công"
        if "manual" in text:
            return "Lệnh thủ công"
        if "auto_command" in text:
            return "Lệnh tự động"
        if "timer-start" in text:
            return "Bắt đầu hẹn giờ"
        if "timer-stop" in text:
            return "Dừng hẹn giờ"
        if "immediate-dry" in text:
            return "Tưới tức thì do đất rất khô"
        if "immediate-stop" in text:
            return "Dừng tưới tức thì"
        if "cooldown" in text:
            return "Đang trong thời gian chờ"
        if "rain" in text:
            return "Quyết định theo thời tiết/mưa"
        return f"Sự kiện: {reason}"

    # ==================================================
    def _ts(self) -> str:
        return datetime.now().isoformat(timespec="seconds")
