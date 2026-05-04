import sys
import ctypes
from PyQt6.QtWidgets import QApplication
from main_window import VideoDownloader

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