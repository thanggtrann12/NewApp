from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLineEdit

class ExampleDialog(QDialog):
    def __init__(self, keyboard):
        super().__init__()
        self.setWindowTitle("Dialog")
        self.keyboard = keyboard

        layout = QVBoxLayout()

        self.lineA = QLineEdit()
        self.lineB = QLineEdit()

        layout.addWidget(self.lineA)
        layout.addWidget(self.lineB)

        self.setLayout(layout)

        self.lineA.installEventFilter(self)
        self.lineB.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == event.MouseButtonPress:
            if isinstance(obj, QLineEdit):
                self.keyboard.popupAt(obj)
        return super().eventFilter(obj, event)
