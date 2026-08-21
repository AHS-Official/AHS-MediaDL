import sys
import os
from PyQt6.QtCore import Qt, qInstallMessageHandler, QtMsgType
from PyQt6.QtWidgets import QApplication
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtGui import QIcon
from gui.main_window import DownloaderApp
from utils.settings import app_config
from gui.theme import apply_theme
from utils import strings
from utils.helpers import get_app_icon

def suppress_qt_warnings(mode, context, message):
    if "Failed to compute left/right minimum bearings" in message:
        return
    if "zwp_text_input_v3_leave" in message or "Got leave event for surface 0x0" in message:
        return
    
    if mode == QtMsgType.QtWarningMsg:
        print(f"Qt Warning: {message}")
    elif mode == QtMsgType.QtCriticalMsg:
        print(f"Qt Critical: {message}")
    elif mode == QtMsgType.QtFatalMsg:
        print(f"Qt Fatal: {message}")

qInstallMessageHandler(suppress_qt_warnings)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("AHS-MediaDL")          
    app.setApplicationDisplayName("AHS-MediaDL")
    
    server_name = "AHS_MediaDL_Unique_Instance"

    # الخطوة 1: محاولة الاتصال بنسخة تعمل فعلياً
    socket = QLocalSocket()
    socket.connectToServer(server_name)
    
    if socket.waitForConnected(500):
        # لو نجح الاتصال، معناه في نسخة شغالة "بجد"
        print("التطبيق يعمل بالفعل، سيتم توجيهك للنسخة الحالية...")
        if len(sys.argv) > 1:
            socket.write(sys.argv[1].encode('utf-8'))
            socket.waitForBytesWritten(500)
        sys.exit(0) 
    else:
        # الخطوة 2: لو فشل الاتصال، نقوم بحذف المقبس القديم
        QLocalServer.removeServer(server_name)

    # الخطوة 3: الآن نبدأ الاستماع كمزود أساسي (Server)
    server = QLocalServer()
    if not server.listen(server_name):
        print("فشل حرج في بدء خادم المقبس.")
        sys.exit(1) 

    startup_url = sys.argv[1] if len(sys.argv) > 1 else None

    # تطبيق الثيم
    apply_theme(app, app_config.get("theme", "auto"))
    app.setWindowIcon(get_app_icon())
    
    # ضبط اتجاه الواجهة (RTL للغة العربية)
    if strings.is_ar:
        app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    else:
        app.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
    
    # تشغيل التطبيق بالاسم الجديد
    window = DownloaderApp(startup_url=startup_url)
    window.show()

    def handle_new_connection():
        client = server.nextPendingConnection()
        if client.waitForReadyRead(500):
            url_data = client.readAll().data().decode('utf-8')
            if url_data:
                window.tabs.setCurrentIndex(0)
                window.tab_home.url_input.setText(url_data)
                window.tab_home.fetch_video_info()

        window.show_normal_and_activate()

    server.newConnection.connect(handle_new_connection)
    
    sys.exit(app.exec())
