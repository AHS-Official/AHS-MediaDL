import sys
import os
import json
import ctypes
if "--listener" in sys.argv:
    from PyQt6.QtWidgets import QApplication, QWidget
    from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation
    from PyQt6.QtNetwork import QLocalSocket, QLocalServer
    from gui.widgets import InteractiveToast
    from utils.locales import tr
    SERVER_NAME = "AHS_MediaDL_SingleInstance_Server"
    LISTENER_SERVER_NAME = "AHS_MediaDL_Listener_Server"
    HOTKEY_ID = 4224

    class BackgroundListener(QWidget):

        def __init__(self):
            super().__init__()
            self.settings_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'settings.json')
            self.hotkey_registered = False
            self.last_monitored_url = ""
            self.init_listener()

        def init_listener(self):
            self.register_global_hotkey()
            clipboard = QApplication.clipboard()
            clipboard.dataChanged.connect(self.on_clipboard_changed)

        def register_global_hotkey(self):
            if sys.platform != 'win32':
                return
            try:
                hwnd = int(self.winId())
                res = ctypes.windll.user32.RegisterHotKey(hwnd, HOTKEY_ID, 0x0002, 0x44)           
                if res:
                    self.hotkey_registered = True
            except Exception:
                pass

        def unregister_global_hotkey(self):
            if sys.platform != 'win32' or not self.hotkey_registered:
                return
            try:
                hwnd = int(self.winId())
                ctypes.windll.user32.UnregisterHotKey(hwnd, HOTKEY_ID)
                self.hotkey_registered = False
            except Exception:
                pass

        def nativeEvent(self, eventType, message):
            if eventType == b"windows_generic_MSG" and sys.platform == 'win32':
                try:
                    from ctypes import wintypes
                    msg = wintypes.MSG.from_address(int(message))
                    if msg.message == 0x0312:            
                        if msg.wParam == HOTKEY_ID:
                            self.on_hotkey_triggered()
                            return True, 0
                except Exception:
                    pass
            return False, 0

        def on_hotkey_triggered(self):
            socket = QLocalSocket()
            socket.connectToServer(SERVER_NAME)
            if socket.waitForConnected(300):
                socket.write(b"TOGGLE")
                socket.waitForBytesWritten(500)
                socket.disconnectFromServer()
            else:
                self.launch_main_app()

        def launch_main_app(self, url=None):
            executable = sys.executable
            app_dir = os.path.dirname(os.path.abspath(__file__))
            main_py = os.path.join(app_dir, "main.py")
            base_exec = os.path.basename(executable).lower()
            is_python = "python" in base_exec or base_exec in ["py.exe", "py"]
            if is_python:
                pythonw = executable.lower().replace("python.exe", "pythonw.exe")
                if os.path.exists(pythonw):
                    args = [pythonw, main_py]
                else:
                    args = [executable, main_py]
            else:
                args = [executable]
            if url:
                args.append(url)
            try:
                import subprocess
                subprocess.Popen(args, cwd=app_dir)
            except Exception:
                pass

        def on_clipboard_changed(self):
            run_in_background = False
            clipboard_monitor = False
            if os.path.exists(self.settings_file):
                try:
                    with open(self.settings_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        run_in_background = data.get("run_in_background", False)
                        clipboard_monitor = data.get("clipboard_monitor", False)
                except Exception:
                    pass
            if not (run_in_background and clipboard_monitor):
                return
            text = QApplication.clipboard().text().strip()
            if not text:
                return
            if self.last_monitored_url == text:
                return
            is_dl_prefix = False
            normalized_text = text
            if text.startswith("dl"):
                is_dl_prefix = True
                normalized_text = text[2:].strip()
                if normalized_text.startswith(":"):
                    normalized_text = normalized_text[1:].strip()
                if not normalized_text.startswith("http"):
                    if "youtube.com" in normalized_text or "youtu.be" in normalized_text:
                        normalized_text = "https://" + normalized_text
            is_youtube = ("youtu.be/" in normalized_text or 
                          "youtube.com/watch" in normalized_text or 
                          "youtube.com/playlist" in normalized_text or
                          "youtube.com/shorts" in normalized_text)
            if is_youtube:
                self.last_monitored_url = text
                socket = QLocalSocket()
                socket.connectToServer(SERVER_NAME)
                if socket.waitForConnected(300):
                    socket.write(normalized_text.encode('utf-8'))
                    socket.waitForBytesWritten(500)
                    socket.disconnectFromServer()
                else:
                    if is_dl_prefix:
                        self.launch_main_app(normalized_text)
                    else:
                        self.toast = InteractiveToast(
                            tr("clipboard_toast_title", "Download Detected"),
                            tr("toast_ask_download", "Do you want to download this video?"),
                            normalized_text,
                            self.launch_main_app,
                            self
                        )
                        self.toast.show()

        def closeEvent(self, event):
            self.unregister_global_hotkey()
            event.accept()
    if sys.platform == 'win32':
        try:
            myappid = 'AHS-MediaDL-Listener' 
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass
    app = QApplication(sys.argv)
    socket = QLocalSocket()
    socket.connectToServer(LISTENER_SERVER_NAME)
    if socket.waitForConnected(300):
        sys.exit(0)                                  
    server = QLocalServer()
    server.removeServer(LISTENER_SERVER_NAME)
    server.listen(LISTENER_SERVER_NAME)
    listener = BackgroundListener()

    def on_listener_connection():
        client_socket = server.nextPendingConnection()
        if client_socket.waitForReadyRead(1000):
            data = client_socket.readAll().data().decode('utf-8').strip()
            if data == "QUIT":
                app.quit()
        client_socket.disconnectFromServer()
    server.newConnection.connect(on_listener_connection)
    listener._ipc_server = server
    sys.exit(app.exec())
else:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtNetwork import QLocalSocket, QLocalServer
    from gui.main_window import VideoDownloader
    SERVER_NAME = "AHS_MediaDL_SingleInstance_Server"
    LISTENER_SERVER_NAME = "AHS_MediaDL_Listener_Server"
    settings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'settings.json')

    def register_protocol_handler():
        if sys.platform != 'win32':
            return
        try:
            import winreg
            executable = sys.executable
            app_dir = os.path.dirname(os.path.abspath(__file__))
            main_py_path = os.path.join(app_dir, "main.py")
            base_exec = os.path.basename(executable).lower()
            is_python = "python" in base_exec or base_exec in ["py.exe", "py"]
            if is_python:
                command = f'"{executable}" "{main_py_path}" "%1"'
            else:
                command = f'"{executable}" "%1"'
            key_path = r"Software\Classes\dl"
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                winreg.SetValue(key, "", winreg.REG_SZ, "URL:dl Protocol")
                winreg.SetValueEx(key, "URL Protocol", 0, winreg.REG_SZ, "")
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path + r"\shell\open\command") as key:
                winreg.SetValue(key, "", winreg.REG_SZ, command)
        except Exception:
            pass

    def spawn_background_listener():
        socket = QLocalSocket()
        socket.connectToServer(LISTENER_SERVER_NAME)
        if socket.waitForConnected(300):
            return                  
        executable = sys.executable
        app_dir = os.path.dirname(os.path.abspath(__file__))
        main_py = os.path.join(app_dir, "main.py")
        base_exec = os.path.basename(executable).lower()
        is_python = "python" in base_exec or base_exec in ["py.exe", "py"]
        if is_python:
            pythonw = executable.lower().replace("python.exe", "pythonw.exe")
            if os.path.exists(pythonw):
                args = [pythonw, main_py, "--listener"]
            else:
                args = [executable, main_py, "--listener"]
        else:
            args = [executable, "--listener"]
        try:
            import subprocess
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.Popen(args, cwd=app_dir, creationflags=subprocess.CREATE_NO_WINDOW, startupinfo=startupinfo)
        except Exception:
            pass
    register_protocol_handler()
    if sys.platform == 'win32':
        try:
            myappid = 'AHS-MediaDL' 
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass
    app = QApplication(sys.argv)
    cli_arg = ""
    if len(sys.argv) > 1:
        cli_arg = sys.argv[1]
    socket = QLocalSocket()
    socket.connectToServer(SERVER_NAME)
    if socket.waitForConnected(500):
        if cli_arg:
            socket.write(cli_arg.encode('utf-8'))
        else:
            socket.write(b"RESTORE")
        socket.waitForBytesWritten(1000)
        sys.exit(0)
    server = QLocalServer()
    server.removeServer(SERVER_NAME)
    server.listen(SERVER_NAME)
    ex = VideoDownloader()

    def on_new_connection():
        client_socket = server.nextPendingConnection()
        if client_socket.waitForReadyRead(1000):
            data = client_socket.readAll().data().decode('utf-8').strip()
            if data == "TOGGLE":
                ex.toggle_window_visibility()
            elif data == "RESTORE":
                ex.restore_window()
            elif data:
                ex.handle_incoming_url(data)
        client_socket.disconnectFromServer()
    server.newConnection.connect(on_new_connection)
    ex._ipc_server = server
    if cli_arg:
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(500, lambda: ex.handle_incoming_url(cli_arg))
    listener_socket = QLocalSocket()
    listener_socket.connectToServer(LISTENER_SERVER_NAME)
    if listener_socket.waitForConnected(300):
        listener_socket.write(b"QUIT")
        listener_socket.waitForBytesWritten(500)
        listener_socket.disconnectFromServer()
    ex.show()
    sys.exit(app.exec())
