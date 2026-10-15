"""
Single Instance & IPC Management for AHS-MediaDL.

Provides single-instance application locking via QLocalServer / QLocalSocket
and background listener process management.
"""

import sys
import os
import subprocess
from PyQt6.QtWidgets import QApplication
from PyQt6.QtNetwork import QLocalSocket, QLocalServer
from PyQt6.QtCore import QTimer

from utils.logger import logger
from managers.system_manager import (
    create_linux_desktop_entry,
    register_protocol_handler,
    set_app_user_model_id,
    register_start_menu_shortcut
)

SERVER_NAME = "AHS_MediaDL_SingleInstance_Server"


def send_ipc_message(server_name: str, data: bytes, timeout: int = 300) -> bool:
    """
    Tries to connect to an existing local IPC server and send data.
    """
    socket = QLocalSocket()
    socket.connectToServer(server_name)
    if socket.waitForConnected(timeout):
        if data:
            socket.write(data)
            socket.waitForBytesWritten(timeout)
        socket.disconnectFromServer()
        return True
    return False


def init_qt_app(app_name: str = "AHS-MediaDL") -> QApplication:
    """Initializes and returns the QApplication instance with standard metadata."""
    try:
        from managers.settings_manager import SettingsManager
        scale = SettingsManager().get("scaling", "auto")
        if scale and scale != "auto":
            os.environ["QT_SCALE_FACTOR"] = str(scale)
    except Exception:
        pass
    app = QApplication(sys.argv)
    app.setApplicationName(app_name)
    app.setApplicationDisplayName(app_name)
    app.setOrganizationName("AHS")
    app.setDesktopFileName(app_name)
    return app


def run_main_app_mode() -> None:
    """Runs the application in standard GUI mode."""
    from gui.main_window import VideoDownloader

    register_protocol_handler()
    create_linux_desktop_entry()
    register_start_menu_shortcut()
    set_app_user_model_id('AHS-MediaDL')

    app = init_qt_app()
    app.setQuitOnLastWindowClosed(False)

    cli_arg = ""
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if not arg.startswith("-"):
                if arg.endswith(".py") or arg.endswith(".exe") or "main.py" in arg:
                    continue
                cli_arg = arg
                break

    ipc_payload = cli_arg.encode('utf-8') if cli_arg else (b"PING" if "--startup" in sys.argv else b"RESTORE")
    if send_ipc_message(SERVER_NAME, ipc_payload, timeout=300):
        sys.exit(0)

    server = QLocalServer()
    server.removeServer(SERVER_NAME)
    server.listen(SERVER_NAME)

    # Check and setup essential binaries (FFmpeg, ffprobe, yt-dlp) if missing
    from managers.binary_manager import BinaryManager
    if not BinaryManager.are_all_tools_available() and "--startup" not in sys.argv:
        from PyQt6.QtWidgets import QDialog
        from gui.components.dialogs.setup_dialog import SetupDialog
        setup = SetupDialog()
        if setup.exec() != QDialog.DialogCode.Accepted:
            if not BinaryManager.are_all_tools_available():
                sys.exit(0)

    ex = VideoDownloader()

    def on_new_connection() -> None:
        client_socket = server.nextPendingConnection()
        if client_socket and client_socket.waitForReadyRead(300):
            data = client_socket.readAll().data().decode('utf-8', errors='replace').strip()
            if data == "TOGGLE":
                ex.toggle_window_visibility()
            elif data == "RESTORE":
                ex.restore_window()
            elif data == "PING":
                pass
            elif data:
                ex.handle_incoming_url(data)
                ex.restore_window()
        if client_socket:
            client_socket.disconnectFromServer()

    server.newConnection.connect(on_new_connection)
    ex._ipc_server = server

    if cli_arg:
        QTimer.singleShot(500, lambda: ex.handle_incoming_url(cli_arg))

    if "--startup" not in sys.argv:
        ex.show()
    else:
        from utils.helpers import trim_working_set_memory
        QTimer.singleShot(1000, trim_working_set_memory)

    sys.exit(app.exec())