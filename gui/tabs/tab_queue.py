import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QProgressBar, QScrollArea, QPushButton, QFrame)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from utils import strings
from gui.theme import styled
from gui.widgets import DownloadQueueItem
from utils.settings import app_config

class DownloadsTab(QWidget):
    active_count_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_app = parent
        self.active_downloads = 0
        self.is_queue_locked = False
        self.initUI()
        
        self.speed_timer = QTimer(self)
        self.speed_timer.timeout.connect(self.update_total_speed)
        self.speed_timer.start(1000)

    def initUI(self):
        tab_queue_layout = QVBoxLayout(self)
        tab_queue_layout.setContentsMargins(20, 20, 20, 20)
        tab_queue_layout.setSpacing(14)

        # --- البار العلوي (العنوان والسرعة وأزرار التحكم السريع) ---
        top_card = QFrame()
        top_card.setObjectName("OptionsCard")
        top_card_layout = QHBoxLayout(top_card)
        top_card_layout.setContentsMargins(14, 12, 14, 12)
        top_card_layout.setSpacing(10)
        
        self.title_lbl = QLabel(strings.TAB_DOWNLOADS if hasattr(strings, 'TAB_DOWNLOADS') else "التنزيلات")
        self.title_lbl.setStyleSheet("font-size: 15px; font-weight: 800;")
        
        self.total_speed_badge = QLabel("🚀 0 KB/s")
        self.total_speed_badge.setStyleSheet("font-size: 11px; font-weight: 700; background: rgba(76, 117, 242, 0.15); color: #4c75f2; border-radius: 6px; padding: 4px 10px;")
        
        top_card_layout.addWidget(self.title_lbl)
        top_card_layout.addWidget(self.total_speed_badge)
        top_card_layout.addStretch()
        
        self.pause_all_btn = QPushButton(strings.BTN_PAUSE_ALL)
        self.pause_all_btn.setFixedHeight(32)
        self.pause_all_btn.clicked.connect(self.pause_all_downloads)
        
        self.cancel_all_btn = styled.danger_button(strings.BTN_CANCEL_ALL)
        self.cancel_all_btn.setFixedHeight(32)
        self.cancel_all_btn.clicked.connect(self.cancel_all_downloads)

        self.clear_done_btn = styled.ghost_button(strings.BTN_CLEAR_COMPLETED)
        self.clear_done_btn.setFixedHeight(32)
        self.clear_done_btn.clicked.connect(self.clear_completed_items)

        top_card_layout.addWidget(self.pause_all_btn)
        top_card_layout.addWidget(self.cancel_all_btn)
        top_card_layout.addWidget(self.clear_done_btn)
        
        tab_queue_layout.addWidget(top_card)

        # --- منطقة السكرول لعرض كروت التحميل ---
        self.queue_area = QScrollArea()
        self.queue_widget = QWidget()
        self.queue_layout = QVBoxLayout(self.queue_widget)
        self.queue_layout.setContentsMargins(0, 0, 0, 0)
        self.queue_layout.setSpacing(8)
        self.queue_layout.addStretch() 
        self.queue_area.setWidget(self.queue_widget)
        self.queue_area.setWidgetResizable(True)
        self.queue_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        tab_queue_layout.addWidget(self.queue_area, stretch=1)

        self.update_button_visibilities()

    def update_button_visibilities(self):
        has_active_or_paused = False
        has_finished = False

        for i in range(self.queue_layout.count()):
            item = self.queue_layout.itemAt(i)
            if item and item.widget():
                state = getattr(item.widget(), 'state', '')
                if state in ["downloading", "waiting", "paused"]:
                    has_active_or_paused = True
                elif state in ["completed", "error", "cancelled"]:
                    has_finished = True

        self.pause_all_btn.setVisible(has_active_or_paused)
        self.cancel_all_btn.setVisible(has_active_or_paused)
        self.clear_done_btn.setVisible(has_finished)

    def _create_and_insert_queue_item(self, url, title, thumb_data, format_id, sub_langs, subs_only, embed_subs, custom_save_dir):
        item = DownloadQueueItem(url, format_id, title, sub_langs, subs_only, embed_subs, custom_save_dir, thumb_data)
        item.download_completed_signal.connect(self.on_download_item_completed)
            
        insert_idx = max(0, self.queue_layout.count() - 1)
        self.queue_layout.insertWidget(insert_idx, item)
        self.manage_queue()

    def manage_queue(self):
        if self.is_queue_locked:
            return 
            
        try: max_downloads = int(app_config.get("concurrent_downloads", 3))
        except: max_downloads = 3

        active_count = 0
        has_active_items = False 
        all_paused = True        

        for i in range(self.queue_layout.count()):
            item = self.queue_layout.itemAt(i)
            if item and item.widget():
                state = getattr(item.widget(), 'state', '')
                if state == "downloading":
                    active_count += 1
                
                if state in ["downloading", "waiting"]:
                    all_paused = False
                    has_active_items = True
                elif state == "paused":
                    has_active_items = True

        self.active_downloads = active_count 

        for i in range(self.queue_layout.count()):
            item = self.queue_layout.itemAt(i)
            if item and item.widget():
                queue_item = item.widget()
                if hasattr(queue_item, 'state'):
                    if queue_item.state in ["downloading", "paused", "cancelled", "completed", "error"]:
                        continue 
                        
                if self.active_downloads < max_downloads:
                    queue_item.start_download()
                    self.active_downloads += 1
                    all_paused = False 
                    has_active_items = True

        if has_active_items and all_paused:
            self.pause_all_btn.setText(strings.BTN_RESUME_ALL)
            self.pause_all_btn.setObjectName("primary")
        else:
            self.pause_all_btn.setText(strings.BTN_PAUSE_ALL)
            self.pause_all_btn.setObjectName("")
            
        self.update_button_visibilities()
        self.active_count_changed.emit(self.active_downloads)
        if self.main_app and hasattr(self.main_app, 'update_downloads_badge'):
            self.main_app.update_downloads_badge(self.active_downloads)

    def on_download_item_completed(self):
        self.active_downloads -= 1 
        self.manage_queue()        

    def pause_all_downloads(self):
        is_pausing = (self.pause_all_btn.text() == strings.BTN_PAUSE_ALL)
        
        self.is_queue_locked = True 
        try:
            for i in range(self.queue_layout.count()):
                item = self.queue_layout.itemAt(i)
                if item and item.widget():
                    queue_item = item.widget()
                    state = getattr(queue_item, 'state', '')
                    
                    if is_pausing:
                        if state in ["downloading", "waiting"] and hasattr(queue_item, 'toggle_pause'):
                            queue_item.toggle_pause()
                    else:
                        if state == "paused" and hasattr(queue_item, 'toggle_pause'):
                            queue_item.toggle_pause()
            
            if is_pausing:
                self.pause_all_btn.setText(strings.BTN_RESUME_ALL)
                self.pause_all_btn.setObjectName("primary")
            else:
                self.pause_all_btn.setText(strings.BTN_PAUSE_ALL)
                self.pause_all_btn.setObjectName("")
        finally:
            self.is_queue_locked = False 
            if not is_pausing:
                self.manage_queue()

    def cancel_all_downloads(self):
        self.is_queue_locked = True 
        try:
            for i in reversed(range(self.queue_layout.count())):
                item = self.queue_layout.itemAt(i)
                if item and item.widget():
                    queue_item = item.widget()
                    if hasattr(queue_item, 'state') and queue_item.state not in ["completed", "cancelled"]:
                        if hasattr(queue_item, 'cancel_action'): queue_item.cancel_action()
            
            self.pause_all_btn.setText(strings.BTN_PAUSE_ALL)
            self.pause_all_btn.setObjectName("")
        finally:
            self.is_queue_locked = False 
            self.manage_queue()

    def clear_completed_items(self):
        self.is_queue_locked = True 
        try:
            for i in reversed(range(self.queue_layout.count())):
                item = self.queue_layout.itemAt(i)
                if item and item.widget():
                    queue_item = item.widget()
                    if hasattr(queue_item, 'state'):
                        if queue_item.state in ["completed", "error", "cancelled"]:
                            self.queue_layout.removeWidget(queue_item)
                            queue_item.deleteLater()
        finally:
            self.is_queue_locked = False
            self.manage_queue()

    def update_total_speed(self):
        total_speed = 0
        for i in range(self.queue_layout.count()):
            item = self.queue_layout.itemAt(i)
            if item and item.widget() and getattr(item.widget(), 'is_downloading', False):
                if hasattr(item.widget(), 'dl_thread'): 
                    total_speed += getattr(item.widget().dl_thread, 'current_speed_bytes', 0)
        
        if total_speed > 1024 * 1024: 
            self.total_speed_badge.setText(f"🚀 {total_speed / (1024 * 1024):.2f} MB/s")
        elif total_speed > 0: 
            self.total_speed_badge.setText(f"🚀 {total_speed / 1024:.2f} KB/s")
        else: 
            self.total_speed_badge.setText("🚀 0 KB/s")
