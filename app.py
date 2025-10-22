import sys
import json
import importlib.util
from PyQt5 import QtWidgets, uic, QtCore

# Load config
with open("config/config.json", "r") as f:
    CONFIG = json.load(f)

# ================= Popup chọn project =================


class ProjectSelectionWindow(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        uic.loadUi("ui/prj_selection_ui.ui", self)
        self.setWindowTitle("Select Project")
        self.selected_project = None
        self.project_buttons = []

        # Layout cho các button project
        self.button_layout = QtWidgets.QVBoxLayout(self.prj_frame)
        self.button_layout.setAlignment(QtCore.Qt.AlignCenter)

        for proj in CONFIG["projects"]:
            btn = QtWidgets.QPushButton(proj["label"])
            btn.setFixedSize(200, 40)
            btn.clicked.connect(
                lambda checked, name=proj["name"]: self.on_project_clicked(name))
            self.button_layout.addWidget(btn)
            self.project_buttons.append(btn)

        self.setFixedSize(300, len(CONFIG["projects"]) * 50 + 50)

    def on_project_clicked(self, project_name):
        self.selected_project = project_name
        self.accept()

# ================= MainApp =================


class MainApp(QtWidgets.QMainWindow):
    def __init__(self, project_name):
        super().__init__()
        uic.loadUi("ui/mainwindow.ui", self)
        self.setWindowTitle(f"{project_name} Control App")

        # Load project config
        self.project_cfg = next(
            (p for p in CONFIG["projects"] if p["name"] == project_name), None)
        if self.project_cfg is None:
            return

        # Dynamic import module
        func_file = self.project_cfg.get("function_file")
        spec = importlib.util.spec_from_file_location(
            "project_module", func_file)
        self.project_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.project_module)

        # ------------------- USB layout -------------------
        self.usb_checkboxes = []
        for usb in self.project_cfg.get("usb_layout", []):
            checkbox = QtWidgets.QCheckBox(usb["text"])
            checkbox.setObjectName(usb["checkbox"])
            self.usb_layout.addWidget(checkbox)
            self.usb_checkboxes.append(checkbox)

            # Connect signal
            checkbox.stateChanged.connect(
                lambda state, cb=checkbox, func_name=usb["execute"]: self.on_usb_checkbox_changed(
                    cb, state, func_name)
            )

        # ------------------- SW flashing layout -------------------
        for sw in self.project_cfg.get("sw_flashing_layout", []):
            btn = QtWidgets.QPushButton(sw["button"])
            btn.clicked.connect(
                lambda _, b=btn, func_name=sw["execute"]: self.on_sw_button_clicked(func_name, b))
            self.sw_flashing_layout.addWidget(btn)
        # ------------------- Reload project button -------------------
        self.prj_reload = self.findChild(QtWidgets.QPushButton, "prj_reload")
        self.prj_reload.clicked.connect(self.reload_project)

    def reload_project(self):
        dlg = ProjectSelectionWindow()
        if dlg.exec_() == QtWidgets.QDialog.Accepted and dlg.selected_project:
            # Close current window and open new
            self.close()
            self.new_window = MainApp(dlg.selected_project)
            self.new_window.show()
    # ------------------- USB checkbox handler -------------------

    def on_usb_checkbox_changed(self, checkbox, state, func_name):
        if state == QtCore.Qt.Checked:
            # Uncheck all other checkboxes in this layout
            for cb in self.usb_checkboxes:
                if cb != checkbox:
                    cb.blockSignals(True)
                    cb.setChecked(False)
                    cb.blockSignals(False)
        # Execute project function
        func = getattr(self.project_module, func_name, None)
        if func:
            func(state)
        # Log action
        self.log(f"{checkbox.text()} {'checked' if state else 'unchecked'}")

    # ------------------- SW button handler -------------------
    def on_sw_button_clicked(self, func_name, button):
        func = getattr(self.project_module, func_name, None)
        if func:
            func()
        # Log ra text của button
        self.log(f"{button.text()} executed")

    # ------------------- Logging -------------------
    def log(self, msg):
        self.log_area.append(msg)
        self.log_area.ensureCursorVisible()


# =================== Main ===================
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    # Project selection
    dlg = ProjectSelectionWindow()
    if dlg.exec_() == QtWidgets.QDialog.Accepted and dlg.selected_project:
        main_window = MainApp(dlg.selected_project)
        main_window.show()
        sys.exit(app.exec_())
