from PyQt5.QtWidgets import (
    QWidget, QPushButton, QGridLayout, QLineEdit,
    QVBoxLayout, QApplication, QFrame
)
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QFont
from PyQt5.QtCore import pyqtSignal
COL_W = 55


class AndroidKeyboard(QWidget):
    textInput = pyqtSignal(str)
    SHIFT_MAP = {
        "1": "!", "2": "@", "3": "#", "4": "$", "5": "%",
        "6": "^", "7": "&", "8": "*", "9": "(", "0": ")",
        "-": "_", "=": "+"
    }

    def __init__(self):
        super().__init__()

        # ==================================================
        # WINDOW (TRONG SUỐT – KHÔNG VẼ NỀN)
        # ==================================================
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)

        # ==================================================
        # STATE
        # ==================================================
        self.shift = False
        self.capslock = False
        self.mode = "alpha"
        self.target = None

        # ==================================================
        # PANEL (CÓ NỀN THẬT)
        # ==================================================
        self.panel = QFrame(self)
        self.panel.setObjectName("KeyboardPanel")
        self.panel.setStyleSheet("""
        #KeyboardPanel {
            background-color: #1E1E1E;
            border: 1px solid #444;
            border-radius: 14px;
        }
        """)

        panel_lay = QVBoxLayout(self.panel)
        panel_lay.setContentsMargins(12, 12, 12, 12)
        panel_lay.setSpacing(0)

        # ==================================================
        # GRID
        # ==================================================
        self.grid = QGridLayout()
        self.grid.setHorizontalSpacing(6)
        self.grid.setVerticalSpacing(6)
        panel_lay.addLayout(self.grid)

        # ==================================================
        # WINDOW LAYOUT
        # ==================================================
        win_lay = QVBoxLayout(self)
        win_lay.setContentsMargins(0, 0, 0, 0)
        win_lay.addWidget(self.panel)

        # ==================================================
        # STYLE BUTTON
        # ==================================================
        self.font = QFont("Arial", 12, QFont.Bold)
        self.setStyleSheet("""
        QPushButton {
            background-color: #2C2C2C;
            border: 1px solid #555;
            border-radius: 8px;
            color: #EEE;
        }
        QPushButton:hover { background-color: #3A3A3A; }
        QPushButton:pressed { background-color: #555; }

        QPushButton[variant="wide"] {
            background-color: #333;
            font-weight: bold;
        }
        QPushButton[shiftState="on"] {
            background-color: #1E88E5;
            color: white;
        }
        QPushButton[shiftState="lock"] {
            background-color: #1565C0;
            color: white;
            font-weight: 800;
        }
        """)

        for c in range(12):
            self.grid.setColumnMinimumWidth(c, COL_W)

        self.cap_btn = None
        self.shift_btn = None
        self.mode_btn = None

        self.build_layout()

    # ==================================================
    # BUILD
    # ==================================================
    def clear_layout(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.cap_btn = self.shift_btn = self.mode_btn = None

    def add_key(self, text, row, col, colspan=1, on_click=None):
        btn = QPushButton(text.replace("&", "&&"))
        btn.setFont(self.font)
        btn.setFixedSize(colspan * COL_W + (colspan - 1) * 6, COL_W)
        btn.setFocusPolicy(Qt.NoFocus)

        if on_click:
            btn.clicked.connect(on_click)
        else:
            btn.clicked.connect(lambda _, k=text: self.press(k))

        self.grid.addWidget(btn, row, col, 1, colspan)
        return btn

    def build_layout(self):
        self.clear_layout()
        if self.mode == "alpha":
            self.build_alpha()
        else:
            self.build_symbol()
        self.update_shift_visual()

    def build_alpha(self):
        for i, k in enumerate("1234567890-="):
            self.add_key(k, 0, i)

        for i, k in enumerate("qwertyuiop"):
            self.add_key(k.upper(), 1, i, on_click=lambda _, kk=k: self.press(kk))
        self.add_key("⌫", 1, 10, colspan=2, on_click=self.backspace)

        self.cap_btn = self.add_key("⇧", 2, 0, on_click=self.toggle_caps)
        for i, k in enumerate("asdfghjkl"):
            self.add_key(k.upper(), 2, 1 + i, on_click=lambda _, kk=k: self.press(kk))
        self.add_key("ENTER", 2, 10, colspan=2, on_click=lambda: self.press("\n"))

        self.shift_btn = self.add_key("SHIFT", 3, 0, colspan=2, on_click=self.toggle_shift)
        for i, k in enumerate("zxcvbnm"):
            self.add_key(k.upper(), 3, 2 + i, on_click=lambda _, kk=k: self.press(kk))

        self.mode_btn = self.add_key("?123", 4, 0, on_click=self.toggle_mode)
        space = self.add_key("SPACE", 4, 1, colspan=10, on_click=lambda: self.press(" "))
        space.setProperty("variant", "wide")

    def build_symbol(self):
        self.shift = False

        for i, k in enumerate("1234567890-="):
            self.add_key(k, 0, i)

        for i, k in enumerate("@#$&_+-()/"):
            self.add_key(k, 1, i)
        self.add_key("⌫", 1, 10, colspan=2, on_click=self.backspace)

        for i, k in enumerate("*\"':;!?.,"):
            self.add_key(k, 2, 1 + i)
        self.add_key("ENTER", 2, 10, colspan=2, on_click=lambda: self.press("\n"))

        self.mode_btn = self.add_key("ABC", 4, 0, on_click=self.toggle_mode)
        space = self.add_key("SPACE", 4, 1, colspan=10, on_click=lambda: self.press(" "))
        space.setProperty("variant", "wide")

    # ==================================================
    # INPUT
    # ==================================================
    def press(self, key):
        # ENTER cho QLineEdit
        if isinstance(self.target, QLineEdit) and key == "\n":
            try:
                self.target.returnPressed.emit()
            except Exception:
                pass
            return

        out = key
        if self.mode == "alpha":
            if key.isalpha():
                out = key.upper() if (self.capslock ^ self.shift) else key.lower()
            elif key in self.SHIFT_MAP and self.shift:
                out = self.SHIFT_MAP[key]
                self.textInput.emit(out)

        if self.target:
            try:
                self.target.insert(out)
            except Exception:
                pass

        # reset shift CHỈ khi gõ ký tự thật
        if self.shift and len(out) == 1 and out not in (" ", "\n"):
            self.shift = False
            self.update_shift_visual()

    def backspace(self):
        if isinstance(self.target, QLineEdit):
            t = self.target.text()
            pos = self.target.cursorPosition()
            if pos > 0:
                self.target.setText(t[:pos - 1] + t[pos:])
                self.target.setCursorPosition(pos - 1)

    def toggle_shift(self):
        self.shift = not self.shift
        self.update_shift_visual()

    def toggle_caps(self):
        self.capslock = not self.capslock
        self.shift = False
        self.update_shift_visual()

    def toggle_mode(self):
        self.mode = "symbol" if self.mode == "alpha" else "alpha"
        self.build_layout()

    def update_shift_visual(self):
        if self.shift_btn:
            self.shift_btn.setProperty("shiftState", "on" if self.shift else "off")
            self.shift_btn.style().polish(self.shift_btn)
        if self.cap_btn:
            self.cap_btn.setProperty("shiftState", "lock" if self.capslock else "off")
            self.cap_btn.setText("⇪" if self.capslock else "⇧")
            self.cap_btn.style().polish(self.cap_btn)

    # ==================================================
    # POPUP
    # ==================================================
    def popupAt(self, widget):
        self.target = widget
        self.setParent(widget.window())
        self.textInput.connect(
        lambda txt: self._insert_to_target(txt)
        )
        self.adjustSize()
        self.move(20, widget.window().height() - self.height() + 50)
        self.show()
        self.raise_()

    def showEvent(self, e):
        QApplication.instance().installEventFilter(self)
        super().showEvent(e)

    def hideEvent(self, e):
        QApplication.instance().removeEventFilter(self)
        super().hideEvent(e)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress:
            w = QApplication.widgetAt(event.globalPos())
            if w and (w is self or self.isAncestorOf(w)):
                return False
            self.hide()
        return False
    def _insert_to_target(self, txt: str):
        if not self.target:
            return

        # QLineEdit
        if hasattr(self.target, "insert"):
            self.target.insert(txt)
            return

        # QTextEdit / QPlainTextEdit
        if hasattr(self.target, "insertPlainText"):
            self.target.insertPlainText(txt)
