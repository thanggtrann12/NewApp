from dataclasses import dataclass
from typing import List


@dataclass
class PumpSchedule:
    """
    Unified & normalized pump schedule
    """
    time: str          # "HH:MM"
    duration: int      # minutes
    days: List[int]    # 0=Mon ... 6=Sun (empty = every day)
