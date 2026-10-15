import socket
import time
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QRunnable, QThreadPool
from managers.settings_manager import SettingsManager


class _PingSignals(QObject):
    result = pyqtSignal(bool)


class _PingRunnable(QRunnable):
    def __init__(self):
        super().__init__()
        self.signals = _PingSignals()

    def run(self):
        connected = False
        for host in [("8.8.8.8", 53), ("1.1.1.1", 53)]:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1.5)
                sock.connect(host)
                sock.close()
                connected = True
                break
            except Exception:
                pass
        self.signals.result.emit(connected)

class NetworkManager(QObject):
    connection_restored = pyqtSignal()
    connection_lost = pyqtSignal()
    status_changed = pyqtSignal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_connected = True
        self._first_check = True
        self._check_in_progress = False
        self.polling_timer = QTimer(self)
        self.polling_timer.timeout.connect(self._check_connection_async)
    
    def start_polling(self, interval_ms=3000):
        if not self.polling_timer.isActive():
            self.polling_timer.start(interval_ms)
        self._check_connection_async()
        
    def stop_polling(self):
        self.polling_timer.stop()

    def is_internet_available(self):
        """فحص سريع متزامن يُستخدم عند الحاجة الفورية."""
        for host in [("8.8.8.8", 53), ("1.1.1.1", 53)]:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1.5)
                sock.connect(host)
                sock.close()
                return True
            except Exception:
                pass
        return False
            
    def _check_connection_async(self):
        if self._check_in_progress:
            return
        self._check_in_progress = True
        runnable = _PingRunnable()
        runnable.signals.result.connect(self._on_ping_result)
        QThreadPool.globalInstance().start(runnable)

    def _on_ping_result(self, currently_connected: bool):
        self._check_in_progress = False
        prev_connected = self.is_connected
        self.is_connected = currently_connected
        
        if self._first_check:
            self._first_check = False
            self.status_changed.emit(currently_connected)
            if not currently_connected:
                self.connection_lost.emit()
        elif prev_connected != currently_connected:
            self.status_changed.emit(currently_connected)
            if currently_connected:
                self.connection_restored.emit()
            else:
                self.connection_lost.emit()


class NetworkTracker(QObject):
    """
    Singleton manager to track total app network usage (RX speed)
    by polling active downloads. 100% thread-safe and stable.
    """
    _instance = None
    _initialized = False

    stats_updated = pyqtSignal(dict)  # emits a dict with speeds and totals

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(NetworkTracker, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        if self.__class__._initialized:
            return
        super().__init__()
        self.__class__._initialized = True
        
        self.settings = SettingsManager()
        self.session_rx = 0
        self.all_time_rx = self.settings.get("all_time_rx", 0)
        self.current_rx_speed = 0
        self.rx_history = [0] * 60
        
        self.save_timer = QTimer(self)
        self.save_timer.timeout.connect(self._save_all_time_stats)
        self.save_timer.start(10000)

        self.last_update_time = None

    def set_current_speed(self, speed_bps):
        """Called from main_window global timer (approx every 0.5s to 1s)"""
        now = time.time()
        if self.last_update_time is not None:
            dt = now - self.last_update_time
            if dt > 5.0 or dt <= 0:
                dt = 0.5
        else:
            dt = 0.5
        self.last_update_time = now
        
        self.current_rx_speed = speed_bps
        added_bytes = int(speed_bps * dt)
        self.session_rx += added_bytes
        self.all_time_rx += added_bytes
        
        self.rx_history.append(self.current_rx_speed)
        if len(self.rx_history) > 60:
            self.rx_history.pop(0)
            
        self.stats_updated.emit(self.get_stats())

    def _save_all_time_stats(self):
        self.settings.set("all_time_rx", self.all_time_rx)

    def get_stats(self):
        return {
            "rx_speed": self.current_rx_speed,
            "tx_speed": 0,
            "session_rx": self.session_rx,
            "session_tx": 0,
            "all_time_rx": self.all_time_rx,
            "all_time_tx": 0,
            "rx_history": list(self.rx_history)
        }