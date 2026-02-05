# utils/global_event_filter.py
from PyQt5.QtCore import QObject, QEvent, QPoint
from PyQt5.QtWidgets import QWidget, QApplication

class GlobalKeyboardEventFilter(QObject):
    """
    Global event filter: tự popup/ẩn/reposition bàn phím ảo cho mọi input.
    Tránh dùng isinstance với lớp Qt để loại trừ RecursionError.
    Không dùng QEvent.Destroy (không đảm bảo có trên mọi build PyQt5).
    """

    def __init__(self, keyboard_widget: QWidget, parent=None):
        super().__init__(parent)
        self.keyboard = keyboard_widget

    # ---- Helpers ------------------------------------------------------------
    def _inherits(self, obj, class_name: str) -> bool:
        """An toàn hơn isinstance: dùng Qt 'inherits' (trả False nếu obj invalid)."""
        try:
            inh = getattr(obj, "inherits", None)
            return bool(inh and inh(class_name))
        except Exception:
            return False

    def _is_text_input(self, obj) -> bool:
        """Nhận diện input dạng văn bản: QLineEdit / QTextEdit / QPlainTextEdit."""
        return (
            self._inherits(obj, "QLineEdit")
            or self._inherits(obj, "QTextEdit")
            or self._inherits(obj, "QPlainTextEdit")
        )

    def _is_keyboard_related(self, obj) -> bool:
        """Bỏ qua sự kiện phát sinh từ chính bàn phím ảo hoặc con của nó."""
        try:
            if obj is self.keyboard:
                return True
            return bool(self.keyboard and self.keyboard.isAncestorOf(obj))
        except Exception:
            return False

    def _reposition(self):
        """Đặt bàn phím ngay dưới target (nếu còn tồn tại)."""
        try:
            target = self.keyboard.target
            if target and isinstance(target, QWidget) and target.isVisible():
                pos = target.mapToGlobal(QPoint(0, target.height() + 4))
                self.keyboard.move(pos)
        except Exception:
            pass

    # ---- Main filter --------------------------------------------------------
    def eventFilter(self, obj, event):
        et = event.type()

        # Bỏ qua chính keyboard và con của nó để tránh vòng lặp
        if self._is_keyboard_related(obj):
            return False

        # 1) Focus/Click vào input -> popup
        if et == QEvent.FocusIn and self._is_text_input(obj):
            self.keyboard.popupAt(obj)
            return False

        if et == QEvent.MouseButtonPress and self._is_text_input(obj):
            self.keyboard.popupAt(obj)
            return False

        # 2) Target di chuyển/resize/show -> reposition
        try:
            if obj is self.keyboard.target and et in (QEvent.Move, QEvent.Resize, QEvent.Show):
                self._reposition()
        except Exception:
            pass

        # 3) Cửa sổ/Widget nói chung di chuyển -> nếu keyboard đang hiện, reposition
        if et in (QEvent.Move, QEvent.Resize) and self.keyboard.isVisible() and getattr(self.keyboard, "target", None):
            self._reposition()

        # 4) FocusOut khỏi input -> ẩn nếu focus không chuyển sang keyboard
        if et == QEvent.FocusOut and self._is_text_input(obj):
            try:
                nf = obj.window().focusWidget()
                if nf and self._is_keyboard_related(nf):
                    return False
            except Exception:
                pass
            if self.keyboard.isVisible():
                self.keyboard.hide()

        # 5) WindowDeactivate -> ẩn (tuỳ bạn có thể bỏ nếu muốn giữ)

        if et == QEvent.WindowDeactivate:
            try:
                aw = QApplication.activeWindow()
                # Nếu không còn cửa sổ nào active (app bị Alt+Tab đi), mới ẩn
                if aw is None and self.keyboard.isVisible():
                    self.keyboard.hide()
            except Exception:
                pass


        # 6) Target bị ẩn/đóng/xoá -> ẩn (không dùng QEvent.Destroy)
        #    Dùng Hide, Close, DeferredDelete là đủ an toàn.
        if obj is getattr(self.keyboard, "target", None) and et in (QEvent.Hide, QEvent.Close, QEvent.DeferredDelete):
            if self.keyboard.isVisible():
                self.keyboard.hide()

        return False