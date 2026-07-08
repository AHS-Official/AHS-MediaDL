import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QScrollArea, QPushButton
from PyQt6.QtCore import Qt, QTimer
from utils import strings
from gui.theme import styled
from gui.widgets import DownloadQueueItem
from utils.settings import app_config

class DownloadsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_app = parent  # الإشارة للنافذة الرئيسية لو احتجنا نكلمها
        self.active_downloads = 0
        self.is_queue_locked = False
        self.initUI()
        
        # تايمر لتحديث السرعة الكلية لكل الكروت الشغالة بانتظام
        self.speed_timer = QTimer(self)
        self.speed_timer.timeout.connect(self.update_total_speed)
        self.speed_timer.start(1000)

    def initUI(self):
        tab_queue_layout = QVBoxLayout(self)

        # --- البار العلوي (السرعة الكلية ونسبة التقدم) ---
        queue_top_bar = QHBoxLayout()
        self.total_speed_label = QLabel(strings.LBL_TOTAL_SPEED + "0 KB/s")
        self.total_progress_bar = QProgressBar() 
        self.total_progress_bar.setFixedHeight(10)
        self.total_progress_bar.setTextVisible(False)
        
        queue_top_bar.addWidget(self.total_speed_label)
        queue_top_bar.addStretch()
        tab_queue_layout.addLayout(queue_top_bar)

        # --- منطقة السكرول لعرض كروت التحميل ---
        self.queue_area = QScrollArea()
        self.queue_widget = QWidget()
        self.queue_layout = QVBoxLayout(self.queue_widget)
        self.queue_layout.addStretch() 
        self.queue_area.setWidget(self.queue_widget)
        self.queue_area.setWidgetResizable(True)
        self.queue_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        tab_queue_layout.addWidget(self.queue_area)

        # --- البار السفلي (أزرار التحكم بالكل) ---
        queue_bottom_bar = QHBoxLayout()
        
        self.pause_all_btn = QPushButton(strings.BTN_PAUSE_ALL)
        self.pause_all_btn.clicked.connect(self.pause_all_downloads)
        
        self.cancel_all_btn = styled.danger_button(strings.BTN_CANCEL_ALL)
        self.cancel_all_btn.clicked.connect(self.cancel_all_downloads)

        self.clear_done_btn = styled.ghost_button(strings.BTN_CLEAR_COMPLETED)
        self.clear_done_btn.clicked.connect(self.clear_completed_items)

        queue_bottom_bar.addWidget(self.pause_all_btn)
        queue_bottom_bar.addWidget(self.cancel_all_btn)
        queue_bottom_bar.addStretch()
        queue_bottom_bar.addWidget(self.clear_done_btn)
        
        tab_queue_layout.addLayout(queue_bottom_bar)

    def _create_and_insert_queue_item(self, url, title, thumb_data, format_id, sub_langs, subs_only, embed_subs, custom_save_dir, custom_metadata=None):
        # إنشاء الكارت الجديد وزرعه في أول القائمة فوق
        item = DownloadQueueItem(url, format_id, title, sub_langs, subs_only, embed_subs, custom_save_dir, thumb_data, custom_metadata)
        item.download_completed_signal.connect(self.on_download_item_completed)
        
        # تحويل إشارة السجل لتسمع في الماين ويندو فوراً عند الاكتمال
        if self.main_app and hasattr(self.main_app, 'save_to_history'):
            item.history_ready_signal.connect(self.main_app.save_to_history)
            
        self.queue_layout.insertWidget(0, item)
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
            self.pause_all_btn.setStyleSheet("") 
        else:
            self.pause_all_btn.setText(strings.BTN_PAUSE_ALL)
            self.pause_all_btn.setObjectName("")
            self.pause_all_btn.setStyleSheet("")

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
                
            self.pause_all_btn.setStyleSheet("") 
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
            self.pause_all_btn.setStyleSheet("")
            
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
            self.total_speed_label.setText(strings.LBL_TOTAL_SPEED + f"{total_speed / (1024 * 1024):.2f} MB/s")
        elif total_speed > 0: 
            self.total_speed_label.setText(strings.LBL_TOTAL_SPEED + f"{total_speed / 1024:.2f} KB/s")
        else: 
            self.total_speed_label.setText(strings.LBL_TOTAL_SPEED + "0 KB/s")
