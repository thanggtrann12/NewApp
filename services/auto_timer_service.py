# services/auto_timer_service.py
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

    def run(self):
        print("[AUTO] AutoTimerService started")
        while self.running:
            try:
                self.tick()
            except Exception as e:
                print("[AUTO] error:", e)
            time.sleep(self.tick_sec)

    def tick(self):
        now = datetime.now()
        print(f"[AUTO TICK] {now.strftime('%H:%M:%S')}")

        for node in self.store.list():
            for idx, schedules in node.pump_schedule.items():
                print(
                    f"[AUTO CHECK] node={node.name} "
                    f"pump={idx+1} "
                    f"mode={node.pump_mode.get(idx)} "
                    f"type={node.auto_type.get(idx)} "
                    f"sched={schedules}"
                )

                if node.pump_mode.get(idx) != "AUTO":
                    print(f"[AUTO SKIP] pump={idx+1} reason=MODE")
                    continue

                if node.auto_type.get(idx) != "TIMER":
                    print(f"[AUTO SKIP] pump={idx+1} reason=TYPE")
                    continue

                running = node.auto_running.get(idx)
                if running:
                    if now >= running["until"]:
                        self._stop_pump(node, idx)
                    else:
                        print(
                            f"[AUTO RUNNING] pump={idx+1} "
                            f"until={running['until'].strftime('%H:%M:%S')}"
                        )
                    continue

                for sch in schedules:
                    time_str = sch[0]
                    duration = int(sch[1])

                    print(
                        f"[AUTO TIME] pump={idx+1} "
                        f"now={now.strftime('%H:%M:%S')} "
                        f"target={time_str}"
                    )

                    t = datetime.strptime(time_str, "%H:%M").replace(
                        year=now.year,
                        month=now.month,
                        day=now.day
                    )

                    if abs((now - t).total_seconds()) <= self.tick_sec:
                        print(
                            f"[AUTO FIRE] node={node.name} "
                            f"pump={idx+1} "
                            f"time={time_str} dur={duration}min"
                        )
                        self._start_pump(
                            node, idx, time_str, duration
                        )
                        break

    # ==================================================
    def _start_pump(self, node, idx, time_str, dur):
        until = datetime.now() + timedelta(minutes=dur)

        node.auto_running[idx] = {
            "until": until,
            "reason": f"TIMER {time_str}"
        }

        node.next_schedule[idx] = (time_str, dur)

        self.bus.send_auto_command(node.id, idx, dur)

    def _stop_pump(self, node, idx):
        print(
            f"[AUTO STOP] node={node.name} "
            f"pump={idx+1}"
        )

        self.bus.send_manual_command(node.id, idx, "OFF")
        node.auto_running.pop(idx, None)
        node.next_schedule.pop(idx, None)
