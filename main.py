import sys
import os
import json
import traceback

# Setup dynamic UI High-DPI Scaling before QApp creation
try:
    from data.settings import app_config
    scaling = app_config.get("ui_scaling", "System Default (Auto)")
    if "100" in scaling:
        os.environ["QT_SCALE_FACTOR"] = "1.0"
    elif "125" in scaling:
        os.environ["QT_SCALE_FACTOR"] = "1.25"
    elif "150" in scaling:
        os.environ["QT_SCALE_FACTOR"] = "1.5"
    elif "200" in scaling:
        os.environ["QT_SCALE_FACTOR"] = "2.0"
except Exception:
    pass

from PyQt6.QtWidgets import QApplication
from gui.main_window import DownloaderApp 
from data.settings import app_config
from gui.theme import apply_theme

# 🛡️ Shield to prevent application from crashing (Core Dump) 🛡️
def global_exception_handler(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    print("\n⚠️ An exception occurred, but the app will continue to run:")
    traceback.print_exception(exc_type, exc_value, exc_traceback)

sys.excepthook = global_exception_handler

def main():
    app = QApplication(sys.argv) 
    
    # Apply theme dynamically on startup (resolves startup styling bug)
    apply_theme(app, app_config.get("theme", "auto"))
    
    window = DownloaderApp()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()