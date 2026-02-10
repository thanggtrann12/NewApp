from PyQt5.QtCore import QObject, QTranslator, QCoreApplication
import os


class LanguageService(QObject):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.current = None
        self.translator = None

    # =========================================
    def load(self, lang: str) -> bool:
        """
        lang: 'vi' | 'en'
        """
        if self.current == lang:
            return True   # 🔥 GUARD – cực quan trọng

        base_dir = os.path.dirname(os.path.dirname(__file__))
        qm_path = os.path.join(
            base_dir,
            "assets", "i18n",
            f"app_{lang}.qm"
        )

        print("[LANG] load:", qm_path)

        if not os.path.exists(qm_path):
            print("[LANG] file not found")
            return False

        # ---- remove old translator
        if self.translator:
            QCoreApplication.removeTranslator(self.translator)

        translator = QTranslator()
        if not translator.load(qm_path):
            print("[LANG] QTranslator.load() failed")
            return False

        QCoreApplication.installTranslator(translator)

        self.translator = translator
        self.current = lang
        print("[LANG] loaded:", lang)
        return True

    # =========================================
    def toggle(self):
        next_lang = "vi" if self.current == "en" else "en"
        return self.load(next_lang)

    # =========================================
    def current_lang(self):
        return self.current
