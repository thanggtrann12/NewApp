# utils/global_event_filter.py
from PyQt5.QtCore import QObject, QEvent, QPoint
from PyQt5.QtWidgets import QWidget, QApplication
from utils.keyboard import AndroidKeyboard
import sip


class GlobalKeyboardEventFilter(QObject):
    """
    Global event filter cho AndroidKeyboard (PyQt5-safe).

    - Dùng sip.isdeleted() để tránh crash
    - Không dùng QPointer (PyQt5 không có)
    - An toàn với QApplication / QObject
    """

    def __init__(self, keyboard_widget: AndroidKeyboard, parent=None):
        super().__init__(parent)
        self.keyboard = keyboard_widget

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _keyboard_alive(self) -> bool:
        try:
            return self.keyboard is not None and not sip.isdeleted(self.keyboard)
        except Exception:
            return False

    def _inherits(self, obj, class_name: str) -> bool:
        try:
            inh = getattr(obj, "inherits", None)
            return bool(inh and inh(class_name))
        except Exception:
            return False

    def _is_text_input(self, obj) -> bool:
        return (
            self._inherits(obj, "QLineEdit")
            or self._inherits(obj, "QTextEdit")
            or self._inherits(obj, "QPlainTextEdit")
        )

    def _is_keyboard_related(self, obj) -> bool:
        try:
            if not self._keyboard_alive():
                return False
            if obj is self.keyboard:
                return True
            return self.keyboard.isAncestorOf(obj)
        except Exception:
            return False

    def _reposition(self):
        try:
            if not self._keyboard_alive():
                return

            target = getattr(self.keyboard, "target", None)
            if not isinstance(target, QWidget):
                return
            if not target.isVisible():
                return

            pos = target.mapToGlobal(QPoint(0, target.height() + 6))
            self.keyboard.move(pos)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Main event filter
    # ------------------------------------------------------------------
    def eventFilter(self, obj, event):
        # keyboard đã bị delete → bỏ qua
        if not self._keyboard_alive():
            return False

        et = event.type()

        # obj không phải QWidget (QApplication, QObject...)
        if not isinstance(obj, QWidget):
            return False

        # bỏ qua event từ keyboard
        if self._is_keyboard_related(obj):
            return False

        # --------------------------------------------------------------
        # 1) Focus / Click vào input -> popup
        # --------------------------------------------------------------
        if et in (QEvent.FocusIn, QEvent.MouseButtonPress) and self._is_text_input(obj):
            if self.keyboard.isVisible() and getattr(self.keyboard, "target", None) is obj:
                return False
            self.keyboard.popupAt(obj)
            return False

        # --------------------------------------------------------------
        # 2) Target move / resize / show -> reposition
        # --------------------------------------------------------------
        if obj is getattr(self.keyboard, "target", None) and et in (
            QEvent.Move, QEvent.Resize, QEvent.Show
        ):
            self._reposition()
            return False

        # --------------------------------------------------------------
        # 3) Window/layout move -> reposition
        # --------------------------------------------------------------
        if et in (QEvent.Move, QEvent.Resize) and self.keyboard.isVisible():
            self._reposition()
            return False

        # --------------------------------------------------------------
        # 4) FocusOut khỏi input -> hide
        # --------------------------------------------------------------
        if et == QEvent.FocusOut and self._is_text_input(obj):
            try:
                fw = obj.window().focusWidget()
                if fw and self._is_keyboard_related(fw):
                    return False
            except Exception:
                pass

            if self.keyboard.isVisible():
                self.keyboard.hide()
            return False

        # --------------------------------------------------------------
        # 5) Window deactivate (Alt+Tab)
        # --------------------------------------------------------------
        if et == QEvent.WindowDeactivate:
            try:
                if QApplication.activeWindow() is None and self.keyboard.isVisible():
                    self.keyboard.hide()
            except Exception:
                pass
            return False

        # --------------------------------------------------------------
        # 6) Target hide / close / delete
        # --------------------------------------------------------------
        if obj is getattr(self.keyboard, "target", None) and et in (
            QEvent.Hide, QEvent.Close, QEvent.DeferredDelete
        ):
            if self.keyboard.isVisible():
                self.keyboard.hide()
            return False

        return False
