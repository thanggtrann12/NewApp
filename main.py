# main.py
import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QStackedWidget, QButtonGroup
)
from PyQt5.QtCore import QFile, QTextStream

from models.store import NodeStore
from models.zone_store import ZoneStore
from widgets.zone_grid import ZoneGrid
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
    def __init__(
        self,
        node_store,
        zone_store,
        bus,
        crop_registry,
        main_window,
        parent=None,
    ):
        super().__init__(parent)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # 🔥 PASS MAIN WINDOW EXPLICITLY
        self.status = StatusBar(
            node_store,
            bus,
            main_window=main_window,
            parent=self
        )
        self.grid = ZoneGrid(
            zone_store,
            node_store,
            bus,
            crop_registry,
            self,
        )

        lay.addWidget(self.status)
        lay.addWidget(self.grid)


# ==============================
# MAIN WINDOW
# ==============================
class MainWindow(QWidget):
    def __init__(self, node_store, zone_store, bus, crop_registry,
                 history, settings):
        super().__init__()
        self.setObjectName("MainWindow")

        self.node_store = node_store
        self.zone_store = zone_store
        self.bus = bus
        self.crop_registry = crop_registry
        self.history = history
        self.settings = settings

        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(0, 0, 0, 0)
        self.root.setSpacing(0)

        # ================= NAV BAR =================
        nav_host = QWidget(self)
        nav_host.setObjectName("MainTabs")
        nav = QHBoxLayout(nav_host)
        nav.setContentsMargins(8, 8, 8, 8)
        nav.setSpacing(8)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)

        self.btn_nodes = QPushButton(self.tr("Khu tưới"))
        self.btn_history = QPushButton(self.tr("Lịch sử"))
        self.btn_settings = QPushButton(self.tr("Cài đặt"))

        for idx, btn in enumerate((
            self.btn_nodes,
            self.btn_history,
            self.btn_settings,
        )):
            btn.setProperty("navTab", "true")
            btn.setCheckable(True)
            self.nav_group.addButton(btn, idx)
            btn.clicked.connect(lambda _, i=idx: self._set_current_page(i))
            nav.addWidget(btn)

        nav.addStretch(1)

        self.root.addWidget(nav_host)

        # ================= STACK =================
        self.stack = QStackedWidget(self)
        self.root.addWidget(self.stack, 1)

        # build pages
        self._build_pages()

        self.stack.currentChanged.connect(self._sync_nav_state)
        self._set_current_page(0)

    def _set_current_page(self, index: int):
        self.stack.setCurrentIndex(index)
        self._sync_nav_state(index)

    def _sync_nav_state(self, index: int):
        btn = self.nav_group.button(index)
        if btn and not btn.isChecked():
            btn.setChecked(True)

    # ==================================================
    # BUILD / REBUILD UI (LANG CHANGE)
    # ==================================================
    def _build_pages(self):
        # clear stack
        while self.stack.count():
            w = self.stack.widget(0)
            self.stack.removeWidget(w)
            w.deleteLater()

        self.nodes_page = AppView(
            self.node_store,
            self.zone_store,
            self.bus,
            self.crop_registry,
            main_window=self,
            parent=self
        )
        self.history_page = HistoryPage(self.history, self)
        self.settings_page = SettingsPage(self.settings, self)

        self.stack.addWidget(self.nodes_page)     # index 0
        self.stack.addWidget(self.history_page)   # index 1
        self.stack.addWidget(self.settings_page)  # index 2

    def rebuild_ui(self):
        """
        Gọi khi cần dựng lại toàn bộ giao diện.
        """
        current = self.stack.currentIndex()
        self._build_pages()
        self.stack.setCurrentIndex(current)
        self._sync_nav_state(current)


# ==============================
# MAIN
# ==============================
if __name__ == '__main__':
    app = QApplication(sys.argv)
    load_stylesheet(app, 'assets/style.qss')

    # ===== SERVICES =====
    history = HistoryService()
    settings = SettingsService()
    crop_registry = CropRegistry()
    node_store = NodeStore('data/nodes.json')
    zone_store = ZoneStore('data/zones.json')

    bus = CentralBus(history)
    transport = SerialTransport(node_store)
    bus.bind_transport(transport)
    transport.start()

    # ===== FIREBASE (optional) =====
    firebase_transport = None
    import os as _os, json as _json
    _fb_cfg = "data/firebase_config.json"
    if _os.path.exists(_fb_cfg):
        try:
            from transport.firebase_transport import FirebaseTransport
            with open(_fb_cfg, encoding="utf-8") as _f:
                _fc = _json.load(_f)

            _credential = _fc["credential"]
            if not _os.path.isabs(_credential):
                _credential = _os.path.normpath(
                    _os.path.join(_os.path.dirname(_fb_cfg), _credential)
                )
            if not _os.path.exists(_credential):
                raise FileNotFoundError(
                    f"credential not found: {_credential}"
                )

            firebase_transport = FirebaseTransport(
                store=node_store,
                bus=bus,
                credential_path=_credential,
                database_url=_fc["database_url"],
                zone_store=zone_store,
                crop_registry=crop_registry,
            )
            started = firebase_transport.start()
            if started:
                print("[FIREBASE] transport started")
            else:
                print("[FIREBASE] transport not started")
        except Exception as _e:
            print(f"[FIREBASE] failed to start: {_e}")

    auto_service = AutoService(
        node_store,
        bus,
        crop_registry,
        zone_store=zone_store,
    )
    # Startup should only calculate schedule preview, not trigger watering.
    auto_service.run(dispatch_commands=False)

    auto_timer = AutoTimerService(node_store, bus)
    auto_timer.start()

    # ===== INPUT =====
    keyboard = AndroidKeyboard()
    gef = GlobalKeyboardEventFilter(keyboard)
    app.installEventFilter(gef)

    # ===== WINDOW =====
    win = MainWindow(
        node_store,
        zone_store,
        bus,
        crop_registry,
        history,
        settings
    )
    win.showFullScreen()
    win.show()

    sys.exit(app.exec_())
