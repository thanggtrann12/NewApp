from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QGridLayout,
    QLabel, QScrollArea, QFrame, QScroller
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap

# =========================
# CROP CARD
# =========================
class CropCard(QFrame):
    clicked = pyqtSignal(object)

    def __init__(self, crop: dict, parent=None):
        super().__init__(parent)
        self.crop = crop

        self.setObjectName("Card")
        self.setFixedSize(180, 200)

        # Quan trọng cho touch + swipe
        self.setAttribute(Qt.WA_AcceptTouchEvents, True)
        self.setFocusPolicy(Qt.NoFocus)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Image
        img = QLabel()
        pix = QPixmap(crop.image)
        if not pix.isNull():
            img.setPixmap(
                pix.scaled(
                    160, 120,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
            )
        img.setAlignment(Qt.AlignCenter)

        # Name
        name = QLabel(crop.name)
        name.setAlignment(Qt.AlignCenter)
        name.setStyleSheet("font-weight: bold;")

        # Suggestion
        suggest = QLabel(crop.suggest_text)
        suggest.setAlignment(Qt.AlignCenter)
        suggest.setStyleSheet("color: #666;")

        layout.addWidget(img)
        layout.addWidget(name)
        layout.addWidget(suggest)

    def mousePressEvent(self, e):
        self.clicked.emit(self.crop)
        e.accept()


# =========================
# SELECT DIALOG
# =========================
class CropSelectDialog(QDialog):
    def __init__(self,  crop_registry, parent=None):
        super().__init__(parent)
        self.selected_crop = None
        self.registry = crop_registry
        self.setWindowTitle(self.tr("Select Crop"))
        self.setModal(True)
        self.resize(420, 360)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        # =========================
        # SCROLL AREA
        # =========================
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.NoFrame)

        # ❌ hide scrollbar – only swipe
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        root.addWidget(self.scroll)

        # =========================
        # CONTAINER + GRID
        # =========================
        container = QFrame()
        grid = QGridLayout(container)
        grid.setSpacing(12)
        grid.setContentsMargins(6, 6, 6, 6)

        r = c = 0
        for crop in self.registry.all():
            card = CropCard(crop)
            card.clicked.connect(self.on_select)
            grid.addWidget(card, r, c, Qt.AlignTop)

            c += 1
            if c >= 2:
                c = 0
                r += 1

        # Push content lên trên
        grid.setRowStretch(r + 1, 1)

        self.scroll.setWidget(container)

        # =========================
        # ENABLE SWIPE (KINETIC)
        # =========================
        QScroller.grabGesture(
            self.scroll.viewport(),
            QScroller.TouchGesture
        )

        # Nếu chạy touch screen thật, dùng dòng này thay cho dòng trên:
        # QScroller.grabGesture(self.scroll.viewport(), QScroller.TouchGesture)

    # =========================
    # ACTION
    # =========================
    def on_select(self, crop: dict):
        self.selected_crop = crop
        self.accept()
