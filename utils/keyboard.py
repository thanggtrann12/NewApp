import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QGridLayout, QLineEdit
)
from PyQt5.QtCore import Qt, QPoint, QEvent
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

COL_W = 55  # 1 ô lưới = 55px

class AndroidKeyboard(QWidget):
    # Bản đồ ký tự khi nhấn Shift (US layout cơ bản) ở CHẾ ĐỘ ABC
    SHIFT_MAP = {
        "1": "!", "2": "@", "3": "#", "4": "$", "5": "%",
        "6": "^", "7": "&", "8": "*", "9": "(", "0": ")",
        "-": "_", "=": "+"
        # Có thể mở rộng thêm:
        # ";": ":", "'": '"', ",": "<", ".": ">", "/": "?",
        # "[": "{", "]": "}", "\\": "|", "`": "~"
    }

    def __init__(self):
        super().__init__()

        # Popup + luôn trên cùng; KHÔNG cướp focus
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)


        # Trạng thái
        self.shift = False          # Shift tạm (chỉ ở ABC)
        self.capslock = False       # Caps Lock toggle (chỉ ở ABC)
        self.target = None
        self.mode = "alpha"         # "alpha" (ABC) | "symbol" (?123)
        self._parent_window = None  # lưu window đang làm parent tạm thời

        # Layout lưới
        self.grid = QGridLayout()
        self.grid.setHorizontalSpacing(5)
        self.grid.setVerticalSpacing(5)
        self.setLayout(self.grid)

        self.font = QFont("Arial", 12, QFont.Bold)

        # ---- Stylesheet: pressed/hover + trạng thái Shift/Caps + biến thể wide (SPACE/ENTER)
        self.setStyleSheet("""
            QPushButton {
                border-radius: 8px;
                background-color: #f0f0f0;
                border: 1px solid;
            }
            QPushButton:hover {
                background-color: #e6e6e6;
            }
            QPushButton:pressed {
                background-color: #d2d2d2;
            }

            /* Biến thể rộng (SPACE/ENTER) */
            QPushButton[variant="wide"] {
                background-color: #d0d0d0;
            }
            QPushButton[variant="wide"]:hover {
                background-color: #c8c8c8;
            }
            QPushButton[variant="wide"]:pressed {
                background-color: #b8b8b8;
            }

            /* Trạng thái hiển thị cho nút Caps/Shift */
            QPushButton[shiftState="off"] {
                background-color: #f0f0f0;
                color: #000;
                font-weight: bold;
            }
            QPushButton[shiftState="on"] {
                background-color: #dbeafe;   /* xanh nhạt khi Shift tạm */
                color: #0a3d91;
                font-weight: bold;
            }
            QPushButton[shiftState="lock"] {
                background-color: #bfdbfe;   /* xanh đậm hơn khi Caps Lock */
                color: #0a3d91;
                font-weight: 800;
                border: 1px solid #0a3d91;
            }
        """)

        # --- CẤU HÌNH LƯỚI CỘT ---
        total_cols = 12
        for c in range(total_cols):
            self.grid.setColumnMinimumWidth(c, COL_W)
            self.grid.setColumnStretch(c, 0)

        # Build bố cục ban đầu (ABC)
        self.build_layout()

    # =======================
    # Building layouts
    # =======================
    def clear_layout(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

        # Xoá tham chiếu nút để tránh dùng nhầm khi ở layout khác
        self.cap_btn = None
        self.shift_btn = None
        self.mode_btn = None

    def add_key(self, text, row, col, w=COL_W, colspan=1, on_click=None, style="", value=None):
        """
        text  : label hiển thị trên nút (ESCAPE '&' -> '&&' để Qt hiển thị đúng ký tự &).
        value : giá trị chèn vào target (mặc định = text nguyên bản, KHÔNG escape).
        """
        btn = QPushButton()

        # Qt dùng '&' làm mnemonic → để HIỂN THỊ '&' phải setText bằng '&&'
        display_text = text.replace("&", "&&")
        btn.setText(display_text)

        btn.setFixedSize(w * colspan + 5 * (colspan - 1), COL_W)
        btn.setFont(self.font)
        if style:
            btn.setStyleSheet(style)
        btn.setFocusPolicy(Qt.NoFocus)

        if on_click:
            btn.clicked.connect(on_click)
        else:
            payload = text if value is None else value
            btn.clicked.connect(lambda _, k=payload: self.press(k))

        self.grid.addWidget(btn, row, col, 1, colspan)
        return btn

    def build_layout(self):
        """Xây layout theo self.mode"""
        self.clear_layout()

        if self.mode == "alpha":
            self.build_alpha_layout()
        else:
            self.build_symbol_layout()

        self.updateShiftVisual()

    def build_alpha_layout(self):
        # --- HÀNG SỐ (row=0) ---
        row0 = 0
        top_row = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "="]
        for i, key in enumerate(top_row):
            self.add_key(key, row0, i, on_click=lambda _, k=key: self.press(k))

        # --- HÀNG QWERTY (row=1) + Backspace ---
        row1 = 1
        qwerty_row = ["q", "w", "e", "r", "t", "y", "u", "i", "o", "p"]
        for i, key in enumerate(qwerty_row):
            self.add_key(key.upper(), row1, i, on_click=lambda _, k=key: self.press(k))
        backspace_btn = self.add_key("⌫", row1, 10, colspan=2, on_click=self.backspace)
        backspace_btn.setProperty("variant", "wide")

        # --- HÀNG ASDF (row=2) + Caps + Enter ---
        row2 = 2
        self.cap_btn = self.add_key("⇧", row2, 0, colspan=1, on_click=self.caplock)
        self.cap_btn.setToolTip("Caps Lock (toggle)")
        self.cap_btn.setProperty("shiftState", "off")
        self.cap_btn.style().unpolish(self.cap_btn); self.cap_btn.style().polish(self.cap_btn)

        asdf_row = ["a", "s", "d", "f", "g", "h", "j", "k", "l"]
        for i, key in enumerate(asdf_row):
            self.add_key(key.upper(), row2, 1 + i, on_click=lambda _, k=key: self.press(k))

        enter_btn = self.add_key("ENTER", row2, 10, colspan=2, on_click=lambda: self.press("\n"))
        enter_btn.setProperty("variant", "wide")
        enter_btn.setToolTip("Enter")
        enter_btn.style().unpolish(enter_btn); enter_btn.style().polish(enter_btn)

        # --- HÀNG Z...M + SHIFT (row=3) ---
        row3 = 3
        col = 0
        self.shift_btn = self.add_key("SHIFT", row3, col, colspan=2, on_click=self.toggleShift)
        self.shift_btn.setToolTip("Shift tạm thời")
        self.shift_btn.setProperty("shiftState", "off")
        self.shift_btn.style().unpolish(self.shift_btn); self.shift_btn.style().polish(self.shift_btn)
        col += 2

        for k in ["z", "x", "c", "v", "b", "n", "m"]:
            self.add_key(k.upper(), row3, col, on_click=lambda _, kk=k: self.press(kk))
            col += 1

        # --- HÀNG SPACE + ?123 (row=4) ---
        row4 = 4
        self.mode_btn = self.add_key("?123", row4, 0, colspan=1, on_click=self.toggleMode)
        self.mode_btn.setToolTip("Chuyển sang số/ký tự")

        space_btn = self.add_key("SPACE", row4, 1, colspan=10, on_click=lambda: self.press(" "))
        space_btn.setProperty("variant", "wide")
        space_btn.setToolTip("Space")
        space_btn.style().unpolish(space_btn); space_btn.style().polish(space_btn)

    def build_symbol_layout(self):
        """
        Layout ?123 (kí tự/số) — KHÔNG có SHIFT, KHÔNG có Caps
        """
        self.shift = False  # tắt shift tạm

        # --- HÀNG SỐ (row=0) ---
        row0 = 0
        top_row = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "="]
        for i, key in enumerate(top_row):
            self.add_key(key, row0, i, on_click=lambda _, k=key: self.press(k))

        # --- HÀNG SYMBOL 1 (row=1) + Backspace ---
        row1 = 1
        sym_row1 = ["@", "#", "$", "_", "&", "-", "+", "(", ")", "/"]
        for i, key in enumerate(sym_row1):
            self.add_key(key, row1, i, on_click=lambda _, k=key: self.press(k))
        self.add_key("⌫", row1, 10, colspan=2, on_click=self.backspace)

        # --- HÀNG SYMBOL 2 (row=2) + ENTER ---
        row2 = 2
        ph = self.add_key("", row2, 0, on_click=None)  # placeholder canh cột
        ph.setEnabled(False)

        sym_row2 = ["*", '"', "'", ":", ";", "!", "?", ",", "."]
        for i, key in enumerate(sym_row2):
            self.add_key(key, row2, 1 + i, on_click=lambda _, k=key: self.press(k))

        enter_btn = self.add_key("ENTER", row2, 10, colspan=2, on_click=lambda: self.press("\n"))
        enter_btn.setProperty("variant", "wide")
        enter_btn.setToolTip("Enter")
        enter_btn.style().unpolish(enter_btn); enter_btn.style().polish(enter_btn)

        # --- HÀNG SYMBOL 3 (row=3) ---
        row3 = 3
        sym_row3 = ["~", "`", "[", "]", "{", "}", "\\", "<", ">", "|"]  # 10 phím lấp 0..9
        for i, k in enumerate(sym_row3):
            self.add_key(k, row3, i, on_click=lambda _, kk=k: self.press(kk))

        # --- HÀNG SPACE + ABC (row=4) ---
        row4 = 4
        self.mode_btn = self.add_key("ABC", row4, 0, colspan=1, on_click=self.toggleMode)
        self.mode_btn.setToolTip("Quay về bàn phím chữ")

        space_btn = self.add_key("SPACE", row4, 1, colspan=10, on_click=lambda: self.press(" "))
        space_btn.setProperty("variant", "wide")
        space_btn.setToolTip("Space")
        space_btn.style().unpolish(space_btn); space_btn.style().polish(space_btn)

    # =======================
    # Input logic
    # =======================
    def press(self, key: str):
        out = key
        if self.mode == "alpha":
            if len(key) == 1:
                if key in self.SHIFT_MAP and self.shift:
                    out = self.SHIFT_MAP[key]
                elif key.isalpha():
                    # XOR giữa capslock và shift
                    is_upper = (self.capslock != self.shift)
                    out = key.upper() if is_upper else key.lower()
                else:
                    out = key
        else:
            out = key  # symbol mode

        if self.target:
            # QLineEdit không xuống dòng
            if isinstance(self.target, QLineEdit) and out == "\n":
                try:
                    self.target.returnPressed.emit()
                except Exception:
                    pass
                if self.shift:
                    self.shift = False
                    self.updateShiftVisual()
                return

            # Chèn ra editor (QLineEdit/QTextEdit/QPlainTextEdit)
            try:
                self.target.insert(out)
            except Exception:
                if hasattr(self.target, "insertPlainText"):
                    self.target.insertPlainText(out)

            # Tắt shift tạm sau khi gõ 1 ký tự ở chế độ ABC
            if self.mode == "alpha" and self.shift and len(out) == 1:
                self.shift = False
                self.updateShiftVisual()

    def toggleShift(self):
        if self.mode != "alpha":
            return
        self.shift = not self.shift
        self.updateShiftVisual()

    def caplock(self):
        if self.mode != "alpha":
            return
        self.capslock = not self.capslock
        if self.capslock:
            self.shift = False
        self.updateShiftVisual()

    def toggleMode(self):
        self.shift = False
        self.mode = "symbol" if self.mode == "alpha" else "alpha"
        self.build_layout()

    def updateShiftVisual(self):
        if hasattr(self, "cap_btn") and self.cap_btn:
            new_state = "lock" if self.capslock else "off"
            if self.cap_btn.property("shiftState") != new_state:
                self.cap_btn.setText("⇪" if self.capslock else "⇧")
                self.cap_btn.setProperty("shiftState", new_state)
                self.cap_btn.style().unpolish(self.cap_btn)
                self.cap_btn.style().polish(self.cap_btn)

        if hasattr(self, "shift_btn") and self.shift_btn:
            new_state = "on" if (self.mode == "alpha" and self.shift) else "off"
            if self.shift_btn.property("shiftState") != new_state:
                self.shift_btn.setProperty("shiftState", new_state)
                self.shift_btn.setEnabled(self.mode == "alpha")
                self.shift_btn.style().unpolish(self.shift_btn)
                self.shift_btn.style().polish(self.shift_btn)

        if hasattr(self, "mode_btn") and self.mode_btn:
            self.mode_btn.setText("ABC" if self.mode == "symbol" else "?123")
            self.mode_btn.setToolTip("Quay về bàn phím chữ" if self.mode == "symbol" else "Chuyển sang số/ký tự")


    def backspace(self):
        if self.target:
            # QLineEdit
            try:
                pos = self.target.cursorPosition()
                if pos > 0:
                    t = self.target.text()
                    self.target.setText(t[:pos-1] + t[pos:])
                    self.target.setCursorPosition(pos-1)
                return
            except Exception:
                pass
            # QTextEdit / QPlainTextEdit
            try:
                cursor = self.target.textCursor()
                cursor.deletePreviousChar()
                self.target.setTextCursor(cursor)
            except Exception:
                pass

    # ---------- chống bị xóa khi dialog đóng ----------
    def _on_parent_destroyed(self, *args):
        """
        Khi window cha (QDialog) sắp bị hủy, tách keyboard ra khỏi parent để
        không bị xóa theo. Sau đó ẩn luôn.
        """
        try:
            self.setParent(None)  # detach => không bị hủy theo cha
            self._parent_window = None
            self.hide()
        except Exception:
            pass

    def popupAt(self, widget):
        """Hiện bàn phím ngay dưới widget target (QLineEdit/QTextEdit, ...),
        hoạt động cả trong QDialog modal và chống tràn 2 chiều.
        """
        self.target = widget

        # Reparent thành child của top-level window chứa target để không bị app-modal block
        try:
            new_parent = widget.window()
            self.setParent(new_parent)
            # Dùng Tool để vẽ ổn định trong dialog, không cướp focus
            self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
            self.setAttribute(Qt.WA_ShowWithoutActivating, True)

            # Ngắt-kết nối cũ (nếu có) rồi kết nối destroyed -> tách parent trước khi cha bị hủy
            if hasattr(self, "_parent_window") and self._parent_window is not None and self._parent_window is not new_parent:
                try:
                    self._parent_window.destroyed.disconnect(self._on_parent_destroyed)
                except Exception:
                    pass
            new_parent.destroyed.connect(self._on_parent_destroyed)
            self._parent_window = new_parent
        except Exception:
            # fallback: không parent
            self.setParent(None)
            self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)

        # Tự ẩn khi target bị destroy
        try:
            widget.destroyed.connect(lambda *_: self.hide())
        except Exception:
            pass

        # Đảm bảo có size trước khi tính
        self.adjustSize()
        kb_w = self.sizeHint().width()
        win_geo = widget.window().frameGeometry()
        # Geometry GLOBAL của cửa sổ cha
        win_geo = widget.window().frameGeometry()
        x = win_geo.x() + (win_geo.width() - kb_w) // 2
        y = win_geo.y() + (win_geo.height() * 2) // 3
        self.move(x, y)


        # (Tùy chọn) style nền để dễ nhìn (bạn có thể bỏ nếu không cần)
        self.setObjectName("KeyboardRoot")
        # Style nền
        self.setStyleSheet("""
            #KeyboardRoot {
                background-color: rgba(30,30,30,0.92);
                border: 1px solid #555;
                border-radius: 10px;
            }
        """)
        self.show()
        try:
            self.raise_()
        except Exception:
            pass

    def _on_parent_destroyed(self, *args):
        try:
            self.setParent(None)  # tách để không bị xóa theo cha
            self.hide()
            self._parent_window = None
        except Exception:
            pass
    def showEvent(self, e):
        """Khi bàn phím hiển thị, lắp event filter toàn cục để bắt click outside."""
        super().showEvent(e)
        try:
            QApplication.instance().installEventFilter(self)
        except Exception:
            pass

    def hideEvent(self, e):
        """Khi bàn phím ẩn, gỡ event filter để tránh tiêu tốn sự kiện không cần thiết."""
        super().hideEvent(e)
        try:
            QApplication.instance().removeEventFilter(self)
        except Exception:
            pass

    def eventFilter(self, obj, event):
        """
        Ẩn bàn phím khi click ra ngoài:
        - Nếu click nằm ngoài self (không phải chính bàn phím hoặc con của nó) -> hide().
        - Vẫn cho sự kiện tiếp tục (return False) để app xử lý bình thường.
        """
        et = event.type()
        if et in (QEvent.MouseButtonPress, QEvent.MouseButtonDblClick):
            try:
                # Vị trí toàn cục của cú click
                gp = event.globalPos()
                # Widget ở vị trí click (có thể None nếu ngoài khu vực app)
                w = QApplication.widgetAt(gp)

                # Nếu click vào chính bàn phím hoặc con của nó -> KHÔNG ẩn
                if w is not None and (w is self or self.isAncestorOf(w)):
                    return False

                # Ngược lại: click outside -> ẩn
                if self.isVisible():
                    self.hide()
            except Exception:
                # Nếu có lỗi, vẫn cứ để sự kiện đi tiếp
                pass

        return False  # không chặn sự kiện gốc
    def move(self, x, y):
        if self.pos().x() == x and self.pos().y() == y:
            return  # không gọi super nếu vị trí giống cũ
        print("move:", x, y)
        super().move(x, y)
