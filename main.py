# main.py
import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout
from PyQt5.QtCore import QFile, QTextStream

from models.store import NodeStore
from widgets.card_grid import CardGrid

# ⬇️ Thêm import
from utils.keyboard import AndroidKeyboard
from utils.global_event_filter import GlobalKeyboardEventFilter

def load_stylesheet(app, path: str):
    f = QFile(path)
    if f.open(QFile.ReadOnly | QFile.Text):
        stream = QTextStream(f)
        app.setStyleSheet(stream.readAll())
        f.close()

class MainWindow(QWidget):
    def __init__(self, store: NodeStore):
        super().__init__()
        self.setWindowTitle('IoT Irrigation System')
        self.resize(860, 520)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(0)
        self.grid = CardGrid(store)
        layout.addWidget(self.grid)

if __name__ == '__main__':
    app = QApplication(sys.argv)

    # 1) Load QSS (nếu có)
    load_stylesheet(app, 'assets/style.qss')

    # 2) Tạo NodeStore
    store = NodeStore('nodes.json')

    # 3) Tạo 1 keyboard duy nhất + cài global filter
    keyboard = AndroidKeyboard()
    gef = GlobalKeyboardEventFilter(keyboard)
    app.installEventFilter(gef)

    # 4) Tạo cửa sổ
    win = MainWindow(store)
    win.show()

    sys.exit(app.exec_())