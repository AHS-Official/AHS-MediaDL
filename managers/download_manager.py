import os
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6 import sip
from core.downloader import DownloadWorker
from utils.locales import tr

class DownloadManager(QObject):
    queue_updated = pyqtSignal()
    download_finished = pyqtSignal(object) # worker
    download_started = pyqtSignal(object) # worker
    network_paused = pyqtSignal()
    network_resumed = pyqtSignal()

    def __init__(self, settings_manager, network_manager):
        super().__init__()
        self.settings = settings_manager
        self.network = network_manager
        self.active_workers = []
        self.waiting_workers = []
        self.zombie_workers = []
        self.is_paused_by_network = False
        
        self.update_max_concurrent()
        
        self.network.connection_restored.connect(self._on_connection_restored)
        self.network.connection_lost.connect(self._on_connection_lost)

    def update_max_concurrent(self):
        c_type = self.settings.get("concurrent_type", "3")
        if c_type == "custom":
            self.max_concurrent = self.settings.get("custom_concurrent_value", 3)
        else:
            try:
                self.max_concurrent = int(c_type)
            except Exception:
                self.max_concurrent = 3

    def reload_download(self, card, url, format_code, save_path, sub_lang=None, is_playlist_sub=False):
        if hasattr(card, 'worker') and card.worker:
            old_worker = card.worker
            if not sip.isdeleted(old_worker):
                self.remove_worker(old_worker)
                try:
                    old_worker.progress_signal.disconnect()
                    old_worker.status_signal.disconnect()
                    old_worker.finished_signal.disconnect()
                    old_worker.finished.disconnect()
                except Exception:
                    pass
                try:
                    if old_worker.isRunning():
                        old_worker.cancel()
                        self.zombie_workers.append(old_worker)
                        old_worker.finished.connect(self._on_worker_finished_cleanup)
                        old_worker.finished.connect(old_worker.deleteLater)
                    else:
                        old_worker.deleteLater()
                except RuntimeError:
                    pass
                    
        card.status_label.setText(tr("status_waiting_queue", "⏳ Waiting in queue..."))
        card.p_bar.setValue(0)
        card.btn_reload.hide()
        card.btn_open.hide()
        card.btn_pause.setToolTip(tr("tooltip_pause", "Pause"))
        card.btn_pause.show()
        card.btn_cancel.show()
        
        worker = DownloadWorker(url, format_code, save_path, sub_lang, is_playlist_sub)
        worker.progress_signal.connect(card.update_progress)
        worker.status_signal.connect(card.update_status)
        worker.finished_signal.connect(card.set_save_path)
        card.set_worker(worker)
        
        # Put back at top of queue
        self.waiting_workers.insert(0, worker)
        self.process_queue()

    def remove_worker(self, worker):
        if worker in self.active_workers:
            self.active_workers.remove(worker)
        if worker in self.waiting_workers:
            self.waiting_workers.remove(worker)

    def add_worker(self, worker, start_immediately=False):
        base_path, ext = os.path.splitext(worker.save_path)
        counter = 1
        new_path = worker.save_path
        
        def is_path_in_use(path):
            norm_p = os.path.normpath(path)
            for w in self.active_workers + self.waiting_workers:
                w_p = getattr(w, 'save_path', None)
                if w_p and os.path.normpath(w_p) == norm_p:
                    return True
            return False

        while is_path_in_use(new_path) or os.path.exists(new_path):
            new_path = f"{base_path}_{counter}{ext}"
            counter += 1
            
        worker.save_path = new_path
        
        self.waiting_workers.append(worker)
        if start_immediately:
            self.process_queue()

    def process_queue(self):
        if self.is_paused_by_network:
            return
            
        self.update_max_concurrent()
        started_any = False
        while len(self.active_workers) < self.max_concurrent and self.waiting_workers:
            worker = self.waiting_workers.pop(0)
            self.active_workers.append(worker)
            worker.finished.connect(self.on_worker_finished)
            worker.start()
            self.download_started.emit(worker)
            started_any = True
            
        if started_any:
            self.queue_updated.emit()

    def on_worker_finished(self):
        worker = self.sender()
        is_conn_err = getattr(worker, 'is_connection_error', False)
        
        self.remove_worker(worker)
        self.download_finished.emit(worker)
        
        if is_conn_err:
            if not self.network.is_internet_available():
                self.is_paused_by_network = True
                self.network.is_connected = False
                self.network.start_polling(5000)
                self.network_paused.emit()
                
        if not self.is_paused_by_network:
            self.process_queue()

    def _on_connection_lost(self):
        self.is_paused_by_network = True
        self.network_paused.emit()

    def _on_connection_restored(self):
        self.is_paused_by_network = False
        self.network_resumed.emit()
        self.process_queue()

    def cancel_all(self):
        for worker in list(self.active_workers):
            try:
                if not sip.isdeleted(worker) and worker.isRunning():
                    worker.cancel()
                    try:
                        worker.finished.disconnect()
                    except Exception:
                        pass
                    self.zombie_workers.append(worker)
                    worker.finished.connect(self._on_worker_finished_cleanup)
                    worker.finished.connect(worker.deleteLater)
            except Exception:
                pass
        self.active_workers.clear()
        self.waiting_workers.clear()

    def _on_worker_finished_cleanup(self):
        worker = self.sender()
        if worker in self.zombie_workers:
            self.zombie_workers.remove(worker)

    def is_path_active(self, path):
        norm_path = os.path.normpath(path)
        for w in self.active_workers + self.waiting_workers:
            w_path = getattr(w, 'save_path', None)
            if w_path and os.path.normpath(w_path) == norm_path:
                return True
        return False