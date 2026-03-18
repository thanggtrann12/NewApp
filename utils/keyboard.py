from PyQt5.QtWidgets import (
    QWidget, QPushButton, QGridLayout, QLineEdit,
    QVBoxLayout, QApplication, QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt, QEvent, QPoint
from PyQt5.QtGui import QFont


class AndroidKeyboard(QWidget):
    SHIFT_MAP = {
        "1": "!", "2": "@", "3": "#", "4": "$", "5": "%",
        "6": "^", "7": "&", "8": "*", "9": "(", "0": ")",
        "-": "_", "=": "+",
        ",": "<", ".": ">", "/": "?"
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
        self._cols = 12
        self._panel_margin = 12
        self._grid_hgap = 6
        self._grid_vgap = 6
        self._key_height = 52

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
        panel_lay.setContentsMargins(
            self._panel_margin,
            self._panel_margin,
            self._panel_margin,
            self._panel_margin,
        )
        panel_lay.setSpacing(0)

        # ==================================================
        # GRID
        # ==================================================
        self.grid = QGridLayout()
        self.grid.setHorizontalSpacing(self._grid_hgap)
        self.grid.setVerticalSpacing(self._grid_vgap)
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
        QPushButton[variant="hide"] {
            background-color: #4A2D36;
            border-color: #6B3D4B;
            color: #FFDDE5;
            font-weight: 800;
        }
        QPushButton[variant="hide"]:hover {
            background-color: #5A3340;
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

        for c in range(self._cols):
            self.grid.setColumnStretch(c, 1)

        self.cap_btn = None
        self.shift_btn = None
        self.mode_btn = None
        self._alpha_key_buttons = []

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
        self._alpha_key_buttons = []

    def add_key(self, text, row, col, colspan=1, on_click=None):
        btn = QPushButton(text.replace("&", "&&"))
        btn.setFont(self.font)
        btn.setFixedHeight(self._key_height)
        btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
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
        self._apply_responsive_metrics()
        self.update_shift_visual()

    def _iter_buttons(self):
        for i in range(self.grid.count()):
            item = self.grid.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), QPushButton):
                yield item.widget()

    def _estimate_key_height(self, host_width: int) -> int:
        inner_width = max(240, host_width - (self._panel_margin * 2))
        per_col = (inner_width - ((self._cols - 1) * self._grid_hgap)) / float(self._cols)
        return int(max(30, min(56, per_col)))

    def _apply_responsive_metrics(self, host=None):
        if host is None:
            host = self._host_window()

        host_width = host.width() if host else 760
        host_height = host.height() if host else 480

        new_key_h = self._estimate_key_height(host_width)

        # Keep keyboard within roughly lower half of host window.
        max_kb_h = int(host_height * 0.5)
        cap_by_height = (max_kb_h - (self._panel_margin * 2) - (self._grid_vgap * 4)) // 5
        new_key_h = max(28, min(new_key_h, cap_by_height if cap_by_height > 0 else new_key_h))

        if new_key_h != self._key_height:
            self._key_height = new_key_h
            for btn in self._iter_buttons():
                btn.setFixedHeight(self._key_height)

        new_font_size = max(10, min(14, int(self._key_height * 0.28)))
        if self.font.pointSize() != new_font_size:
            self.font.setPointSize(new_font_size)
            for btn in self._iter_buttons():
                btn.setFont(self.font)

    def build_alpha(self):
        for i, k in enumerate("1234567890-="):
            self.add_key(k, 0, i)

        for i, k in enumerate("qwertyuiop"):
            btn = self.add_key(k, 1, i, on_click=lambda _, kk=k: self.press(kk))
            self._alpha_key_buttons.append((k, btn))
        self.add_key("⌫", 1, 10, colspan=2, on_click=self.backspace)

        self.cap_btn = self.add_key("⇧", 2, 0, on_click=self.toggle_caps)
        for i, k in enumerate("asdfghjkl"):
            btn = self.add_key(k, 2, 1 + i, on_click=lambda _, kk=k: self.press(kk))
            self._alpha_key_buttons.append((k, btn))
        self.add_key("ENTER", 2, 10, colspan=2, on_click=lambda: self.press("\n"))

        self.shift_btn = self.add_key("SHIFT", 3, 0, colspan=2, on_click=self.toggle_shift)
        for i, k in enumerate("zxcvbnm"):
            btn = self.add_key(k, 3, 2 + i, on_click=lambda _, kk=k: self.press(kk))
            self._alpha_key_buttons.append((k, btn))
        self.add_key(",", 3, 9)
        self.add_key(".", 3, 10)
        self.add_key("/", 3, 11)

        self.mode_btn = self.add_key("?123", 4, 0, on_click=self.toggle_mode)
        space = self.add_key("SPACE", 4, 1, colspan=10, on_click=lambda: self.press(" "))
        space.setProperty("variant", "wide")
        hide_btn = self.add_key("ẨN", 4, 11, on_click=self.hide_keyboard)
        hide_btn.setProperty("variant", "hide")

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
        hide_btn = self.add_key("ẨN", 4, 11, on_click=self.hide_keyboard)
        hide_btn.setProperty("variant", "hide")

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

    def _refresh_alpha_keycaps(self):
        is_upper = self.capslock ^ self.shift
        for key, btn in self._alpha_key_buttons:
            label = key.upper() if is_upper else key.lower()
            btn.setText(label.replace("&", "&&"))

    def hide_keyboard(self):
        self.hide()

    def update_shift_visual(self):
        self._refresh_alpha_keycaps()

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
        if not isinstance(widget, QWidget):
            return

        self.target = widget
        host = widget.window()
        if self.parent() is not host:
            self.setParent(host)

        self.reposition()
        self.show()
        self.raise_()

    def reposition(self):
        host = self._host_window()
        if not host:
            return

        margin = 10
        self.setFixedWidth(max(260, host.width() - (margin * 2)))
        self._apply_responsive_metrics(host)
        self.adjustSize()

        kb_w = self.width()
        kb_h = self.height()

        if kb_w + (margin * 2) >= host.width():
            local_x = max(0, (host.width() - kb_w) // 2)
        else:
            local_x = margin
            try:
                target_local_x = self.target.mapTo(host, QPoint(0, 0)).x()
                max_local_x = host.width() - kb_w - margin
                local_x = min(max(target_local_x, margin), max_local_x)
            except Exception:
                pass

        local_y = max(margin, host.height() - kb_h - margin)
        self.move(local_x, local_y)

    def _host_window(self):
        if isinstance(self.parent(), QWidget):
            return self.parent()
        if isinstance(self.target, QWidget):
            try:
                return self.target.window()
            except Exception:
                return None
        return None

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
