# main.py
import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout
from PyQt5.QtCore import QFile, QTextStream
from models.store import NodeStore
from widgets.card_grid import CardGrid
from widgets.status_bar import StatusBar

from utils.keyboard import AndroidKeyboard
from utils.global_event_filter import GlobalKeyboardEventFilter
from services.serial_service import SerialListener, SerialNodeBus
from services.auto_service import AutoService
from services.auto_timer_service import AutoTimerService
from services.crop_registry import CropRegistry
from services.language_service import LanguageService

def load_stylesheet(app, path: str):
    f = QFile(path)
    if f.open(QFile.ReadOnly | QFile.Text):
        stream = QTextStream(f)
        app.setStyleSheet(stream.readAll())
        f.close()
class AppView(QWidget):
    def __init__(self, store, bus, crop_registry, lang_service, parent=None):
        super().__init__(parent)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.status = StatusBar(store, bus, lang_service, self)
        self.grid = CardGrid(store, bus, crop_registry, self)

        lay.addWidget(self.status)
        lay.addWidget(self.grid)

class MainWindow(QWidget):
    def __init__(self, store, bus, crop_registry, lang_service):
        super().__init__()
        self.store = store
        self.bus = bus
        self.crop_registry = crop_registry
        self.lang_service = lang_service

        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(0, 0, 0, 0)
        self.root.setSpacing(0)

        self.app = None
        self.rebuild_ui()

    def rebuild_ui(self):
        if self.app:
            self.root.removeWidget(self.app)
            self.app.deleteLater()
            self.app = None

        self.app = AppView(
            self.store,
            self.bus,
            self.crop_registry,
            self.lang_service,
            parent=self
        )
        self.root.addWidget(self.app)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    load_stylesheet(app, 'assets/style.qss')

    crop_registry = CropRegistry()
    store = NodeStore('data/nodes.json')
    bus = SerialNodeBus(store)
    auto_service = AutoService(bus, store, crop_registry)
    keyboard = AndroidKeyboard()
    gef = GlobalKeyboardEventFilter(keyboard)
    app.installEventFilter(gef)

    auto_service.run()

    lang_service = LanguageService(app)

    listener = SerialListener(bus, store)
    listener.start()

    auto_timer = AutoTimerService(store, bus)
    auto_timer.start()
    lang_service = LanguageService(app)
    lang_service.load("vi")

    win = MainWindow(store, bus, crop_registry, lang_service)
    win.showFullScreen()
    win.show()

    sys.exit(app.exec_())