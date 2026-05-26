import sys
import ctypes
import os
import sys
import json
from PyQt6.QtWidgets import QApplication
from gui.main_window import VideoDownloader

settings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'settings.json')
if os.path.exists(settings_path):
    try:
        with open(settings_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            scaling = data.get("scaling", "auto")
            if scaling != "auto":
                os.environ["QT_SCALE_FACTOR"] = str(scaling)
    except Exception:
        pass

if 'QT_STYLE_OVERRIDE' in os.environ:
    del os.environ['QT_STYLE_OVERRIDE']

if __name__ == '__main__':
    if sys.platform == 'win32':
        try:
            myappid = 'ahs.mediadl.pro.version1' 
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass
    app = QApplication(sys.argv)
    ex = VideoDownloader()
    ex.show()
    sys.exit(app.exec())