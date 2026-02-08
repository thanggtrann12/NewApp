# main.py
import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout
from PyQt5.QtCore import QFile, QTextStream
from PyQt5.QtWidgets import QScroller
from PyQt5.QtCore import Qt

from models.store import NodeStore
from widgets.card_grid import CardGrid

from PyQt5.QtWidgets import QScroller
from PyQt5.QtCore import Qt
from utils.keyboard import AndroidKeyboard
from utils.global_event_filter import GlobalKeyboardEventFilter
from services.serial_service import SerialListener, SerialNodeBus
from services.auto_service import AutoService
from services.auto_timer_service import AutoTimerService

def load_stylesheet(app, path: str):
    f = QFile(path)
    if f.open(QFile.ReadOnly | QFile.Text):
        stream = QTextStream(f)
        app.setStyleSheet(stream.readAll())
        f.close()

class MainWindow(QWidget):
    def __init__(self, store: NodeStore, bus: SerialNodeBus):
        super().__init__()
        self.bus = bus
        self.setWindowTitle('IoT Irrigation System')

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.grid = CardGrid(store, bus)
        layout.addWidget(self.grid)

        QScroller.grabGesture(
            self.grid,
            QScroller.LeftMouseButtonGesture
        )

if __name__ == '__main__':
    app = QApplication(sys.argv)

    # 1) Load QSS (nếu có)
    load_stylesheet(app, 'assets/style.qss')

    # 2) Tạo NodeStore
    store = NodeStore('nodes.json')
    bus = SerialNodeBus(store)
    auto_service = AutoService(bus, store)
    auto_service.run()

    # 3) Tạo 1 keyboard duy nhất + cài global filter
    keyboard = AndroidKeyboard()
    gef = GlobalKeyboardEventFilter(keyboard)
    app.installEventFilter(gef)

    # 4) Tạo cửa sổ
    win = MainWindow(store, bus)
    listener = SerialListener(bus, store)
    listener.start()
    
    auto_timer = AutoTimerService(store, bus)
    auto_timer.start()

    win.showFullScreen()
    win.show()

    sys.exit(app.exec_())