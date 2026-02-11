import json
from PyQt5.QtCore import QObject, pyqtSignal


class SettingsService(QObject):
    changed = pyqtSignal(dict)

    DEFAULT = {
        "auto_timer": {
            "tick_sec": 30,
            "tolerance_sec": 30
        },
        "auto_recommend": {
            "enabled": True,
            "startup_delay_sec": 10
        },
        "dev": {
            "log_level": "INFO"
        }
    }

    def __init__(self, path="data/settings.json", parent=None):
        super().__init__(parent)
        self.path = path
        self.data = self.DEFAULT.copy()
        self.load()

    def load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                self.data.update(json.load(f))
        except Exception:
            pass

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    def update(self, new_data: dict):
        self.data.update(new_data)
        self.save()
        self.changed.emit(self.data)
