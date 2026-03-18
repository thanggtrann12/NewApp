import threading
import time
from datetime import datetime, timedelta


class AutoTimerService(threading.Thread):
    def __init__(self, store, bus, tick_sec=30):
        super().__init__(daemon=True)
        self.store = store
        self.bus = bus
        self.tick_sec = tick_sec
        self.running = True

        print(
            f"[AutoTimer] init tick_sec={tick_sec}s"
        )

    # ==================================================
    def run(self):
        print("[AutoTimer] thread started")

        while self.running:
            try:
                self.tick()
            except Exception as e:
                print(f"[AutoTimer][ERROR] tick failed: {e}")

            time.sleep(self.tick_sec)

        print("[AutoTimer] thread stopped")

    # ==================================================
    def tick(self):
        now = datetime.now()
        print(
            f"[AutoTimer] tick @ {now.strftime('%H:%M:%S')}"
        )

        for node in self.store.list():
            node_id = getattr(node, "id", "?")
            print(f"[AutoTimer] check node={node_id}")

            for idx, schedules in node.pump_schedule.items():
                mode = node.pump_mode.get(idx, "AUTO")
                auto_type = node.auto_type.get(idx, "SCHEDULE")
                if auto_type == "RECOMMEND":
                    auto_type = "SCHEDULE"

                print(
                    f"  ├─ pump {idx+1} "
                    f"mode={mode} "
                    f"type={auto_type}"
                )

                if mode != "AUTO":
                    print("  │  skip: not AUTO")
                    continue

                if auto_type != "TIMER":
                    print("  │  skip: not TIMER")
                    continue

                running = node.auto_running.get(idx)
                if running:
                    until = running.get("until")
                    print(
                        f"  │  running until "
                        f"{until.strftime('%H:%M:%S')}"
                    )

                    if now >= until:
                        print(
                            f"  │  stop pump {idx+1}"
                        )
                        self._stop(node, idx)
                    continue

                for sch in schedules:
                    t = datetime.strptime(
                        sch.time, "%H:%M"
                    ).replace(
                        year=now.year,
                        month=now.month,
                        day=now.day
                    )

                    diff = abs(
                        (now - t).total_seconds()
                    )

                    print(
                        f"  │  check schedule "
                        f"{sch.time} ({sch.duration}m) "
                        f"Δ={int(diff)}s"
                    )

                    if diff <= self.tick_sec:
                        print(
                            f"  │  START pump {idx+1} "
                            f"for {sch.duration} min"
                        )
                        self._start(node, idx, sch)
                        break

    # ==================================================
    def _start(self, node, idx, sch):
        until = datetime.now() + timedelta(
            minutes=sch.duration
        )

        node.auto_running[idx] = {"until": until}
        node.next_schedule[idx] = (sch.time, sch.duration)
        node.auto_reason = getattr(node, "auto_reason", {})
        node.auto_reason[idx] = (
            f"timer-start({sch.time}/{sch.duration}m)"
        )

        print(
            f"[AutoTimer] ▶ START "
            f"node={node.id} pump={idx+1} "
            f"until={until.strftime('%H:%M:%S')}"
        )
        self.bus.send_auto(node, idx, sch.duration)

    # ==================================================
    def _stop(self, node, idx):
        print(
            f"[AutoTimer] ■ STOP "
            f"node={node.id} pump={idx+1}"
        )
        node.auto_reason = getattr(node, "auto_reason", {})
        prev = node.auto_reason.get(idx, "")
        tail = "timer-stop(timeout)"
        node.auto_reason[idx] = f"{prev}, {tail}" if prev else tail

        self.bus.send_manual(node.id, idx, "OFF")
        node.auto_running.pop(idx, None)
        node.next_schedule.pop(idx, None)
