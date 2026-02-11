# main.py
import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QStackedWidget
)
from PyQt5.QtCore import QFile, QTextStream

from models.store import NodeStore
from widgets.card_grid import CardGrid
from widgets.status_bar import StatusBar
from widgets.history import HistoryService, HistoryPage
from widgets.settings import SettingsPage

from bus.central_bus import CentralBus
from transport.serial_transport import SerialTransport

from utils.keyboard import AndroidKeyboard
from utils.global_event_filter import GlobalKeyboardEventFilter
from services.auto_service import AutoService
from services.auto_timer_service import AutoTimerService
from services.crop_registry import CropRegistry
from services.language_service import LanguageService
from services.settings_service import SettingsService


# ==============================
# LOAD STYLE
# ==============================
def load_stylesheet(app, path: str):
    f = QFile(path)
    if f.open(QFile.ReadOnly | QFile.Text):
        stream = QTextStream(f)
        app.setStyleSheet(stream.readAll())
        f.close()


# ==============================
# APP VIEW = NODES PAGE
# ==============================
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


# ==============================
# MAIN WINDOW
# ==============================
class MainWindow(QWidget):
    def __init__(self, store, bus, crop_registry, lang_service,
                 history, settings):
        super().__init__()

        self.store = store
        self.bus = bus
        self.crop_registry = crop_registry
        self.lang_service = lang_service
        self.history = history
        self.settings = settings

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ================= NAV BAR =================
        nav = QHBoxLayout()
        nav.setContentsMargins(8, 8, 8, 8)
        nav.setSpacing(8)

        btn_nodes = QPushButton(self.tr("Nodes"))
        btn_history = QPushButton(self.tr("History"))
        btn_settings = QPushButton(self.tr("Settings"))

        nav.addWidget(btn_nodes)
        nav.addWidget(btn_history)
        nav.addWidget(btn_settings)
        nav.addStretch(1)

        root.addLayout(nav)

        # ================= STACK =================
        self.stack = QStackedWidget(self)

        self.nodes_page = AppView(
            store, bus, crop_registry, lang_service, self
        )
        self.history_page = HistoryPage(history, self)
        self.settings_page = SettingsPage(settings, self)

        self.stack.addWidget(self.nodes_page)     # index 0
        self.stack.addWidget(self.history_page)   # index 1
        self.stack.addWidget(self.settings_page)  # index 2

        root.addWidget(self.stack, 1)

        # ================= NAV ACTIONS =================
        btn_nodes.clicked.connect(
            lambda: self.stack.setCurrentIndex(0)
        )
        btn_history.clicked.connect(
            lambda: self.stack.setCurrentIndex(1)
        )
        btn_settings.clicked.connect(
            lambda: self.stack.setCurrentIndex(2)
        )


# ==============================
# MAIN
# ==============================
if __name__ == '__main__':
    app = QApplication(sys.argv)
    load_stylesheet(app, 'assets/style.qss')
    history = HistoryService()
    settings = SettingsService()
    # ===== CORE SERVICES =====
    crop_registry = CropRegistry()
    store = NodeStore('data/nodes.json')

    bus = CentralBus(history)
    transport = SerialTransport(store)
    bus.bind_transport(transport)
    transport.start()

    auto_service = AutoService(store, bus, crop_registry)
    auto_service.run()

    auto_timer = AutoTimerService(store, bus)
    auto_timer.start()

    # ===== INPUT =====
    keyboard = AndroidKeyboard()
    gef = GlobalKeyboardEventFilter(keyboard)
    app.installEventFilter(gef)

    # ===== LANGUAGE =====
    lang_service = LanguageService(app)
    lang_service.load("vi")

    # ===== HISTORY + SETTINGS =====


    # ===== WINDOW =====
    win = MainWindow(
        store,
        bus,
        crop_registry,
        lang_service,
        history,
        settings
    )
    win.showFullScreen()
    win.show()

    sys.exit(app.exec_())
