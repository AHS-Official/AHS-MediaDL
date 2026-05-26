"""
Downloads Page — Queue management for active, paused, and completed downloads.
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QScrollArea, QPushButton, QProgressBar, QFrame)
from PyQt6.QtCore import QTimer, Qt
from data.settings import app_config
from gui.widgets import DownloadQueueItem
from utils import helpers


class DownloadsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.active_downloads = 0
        self.init_ui()
        
        # Speed tracking timer
        self.speed_timer = QTimer(self)
        self.speed_timer.timeout.connect(self.update_total_speed)
        self.speed_timer.start(1000)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 24, 20, 20)
        layout.setSpacing(15)

        queue_top_bar = QHBoxLayout()
        self.total_speed_label = QLabel(helpers.LBL_TOTAL_SPEED + "0 KB/s")
        self.total_speed_label.setObjectName("heading")
        self.total_speed_label.setStyleSheet("font-size: 12pt; font-weight: 700;")
        
        self.total_progress_bar = QProgressBar() 
        self.total_progress_bar.setFixedHeight(10)
        self.total_progress_bar.setTextVisible(False)
        
        queue_top_bar.addWidget(self.total_speed_label)
        queue_top_bar.addStretch()
        layout.addLayout(queue_top_bar)

        # Scrolling area for list of Cards
        self.queue_area = QScrollArea()
        self.queue_area.setWidgetResizable(True)
        self.queue_area.setStyleSheet("background-color: transparent; border: none;")
        self.queue_widget = QWidget()
        self.queue_widget.setStyleSheet("background-color: transparent;")
        self.queue_layout = QVBoxLayout(self.queue_widget)
        self.queue_layout.setContentsMargins(0, 0, 0, 0)
        self.queue_layout.setSpacing(10)
        self.queue_layout.addStretch() 
        self.queue_area.setWidget(self.queue_widget)
        
        # Centered Empty State Placeholder (Step 2)
        self.placeholder_widget = QFrame()
        self.placeholder_widget.setObjectName("GlowCard")
        self.placeholder_widget.setMinimumHeight(240)
        ph_layout = QVBoxLayout(self.placeholder_widget)
        ph_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ph_layout.setSpacing(15)
        
        self.ph_icon = QLabel()
        self.ph_icon.setPixmap(helpers.get_theme_icon("download.svg", 80).pixmap(80, 80))
        self.ph_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        ph_text = "لا توجد تنزيلات جارية حالياً. ضع رابطاً في الصفحة الرئيسية لبدء التحميل" if helpers.is_ar else "No downloads in progress. Paste a link on the Home page to start downloading"
        self.ph_lbl = QLabel(ph_text)
        self.ph_lbl.setObjectName("hint")
        self.ph_lbl.setStyleSheet("font-size: 12pt; font-weight: 500;")
        self.ph_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ph_lbl.setWordWrap(True)
        
        ph_layout.addWidget(self.ph_icon)
        ph_layout.addWidget(self.ph_lbl)
        
        layout.addWidget(self.placeholder_widget, stretch=1)
        layout.addWidget(self.queue_area, stretch=1)

        # Context-Aware global queue controls bar
        self.queue_bottom_bar_widget = QWidget()
        queue_bottom_bar = QHBoxLayout(self.queue_bottom_bar_widget)
        queue_bottom_bar.setContentsMargins(0, 0, 0, 0)
        queue_bottom_bar.setSpacing(10)
        
        self.pause_all_btn = QPushButton(helpers.BTN_PAUSE_ALL)
        self.pause_all_btn.clicked.connect(self.pause_all_downloads)
        
        self.cancel_all_btn = QPushButton(helpers.BTN_CANCEL_ALL)
        self.cancel_all_btn.setObjectName("danger")
        self.cancel_all_btn.clicked.connect(self.cancel_all_downloads)

        self.clear_done_btn = QPushButton(helpers.BTN_CLEAR_COMPLETED)
        self.clear_done_btn.clicked.connect(self.clear_completed_items)

        queue_bottom_bar.addWidget(self.pause_all_btn)
        queue_bottom_bar.addWidget(self.cancel_all_btn)
        queue_bottom_bar.addStretch()
        queue_bottom_bar.addWidget(self.clear_done_btn)
        
        layout.addWidget(self.queue_bottom_bar_widget)
        
        # Hide context-aware controls initially
        self.queue_bottom_bar_widget.hide()
        self.update_placeholder_visibility()

    # ──────────────────────────────────────────────
    #  Queue Item Management
    # ──────────────────────────────────────────────

    def add_queue_item(self, url, title, thumb_data, format_id, sub_langs, subs_only, embed_subs, custom_save_dir):
        item = DownloadQueueItem(url, format_id, title, sub_langs, subs_only, embed_subs, custom_save_dir, thumb_data)
        item.download_completed_signal.connect(self.on_download_item_completed)
        self.queue_layout.insertWidget(0, item)
        self.update_global_controls_visibility()
        self.update_placeholder_visibility()

    def manage_queue(self):
        if getattr(self, 'is_queue_locked', False): return 
            
        try: max_downloads = int(app_config.get("concurrent_downloads", 3))
        except: max_downloads = 3

        active_count = 0
        has_active_items = False 
        all_paused = True        

        for i in range(self.queue_layout.count()):
            item = self.queue_layout.itemAt(i)
            if item and item.widget():
                state = getattr(item.widget(), 'state', '')
                if state == "downloading": active_count += 1
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
            self.pause_all_btn.setText(helpers.BTN_RESUME_ALL)
            self.pause_all_btn.setObjectName("primary")
            self.pause_all_btn.style().polish(self.pause_all_btn)
        else:
            self.pause_all_btn.setText(helpers.BTN_PAUSE_ALL)
            self.pause_all_btn.setObjectName("") 
            self.pause_all_btn.style().polish(self.pause_all_btn)
            
        self.update_global_controls_visibility()
        self.update_placeholder_visibility()

    def update_global_controls_visibility(self):
        # Context-aware global queue action panel visibility
        has_items = False
        for i in range(self.queue_layout.count()):
            item = self.queue_layout.itemAt(i)
            if item and item.widget():
                state = getattr(item.widget(), 'state', '')
                if state in ["downloading", "waiting", "paused"]:
                    has_items = True
                    break
        
        self.queue_bottom_bar_widget.setVisible(has_items)

    def on_download_item_completed(self):
        self.manage_queue()        

    # ──────────────────────────────────────────────
    #  Global Queue Controls
    # ──────────────────────────────────────────────

    def pause_all_downloads(self):
        is_pausing = (self.pause_all_btn.text() == helpers.BTN_PAUSE_ALL)
        self.is_queue_locked = True 
        try:
            for i in range(self.queue_layout.count()):
                item = self.queue_layout.itemAt(i)
                if item and item.widget():
                    queue_item = item.widget()
                    state = getattr(queue_item, 'state', '')
                    if is_pausing:
                        if state in ["downloading", "waiting"] and hasattr(queue_item, 'toggle_pause'): queue_item.toggle_pause()
                    else:
                        if state == "paused" and hasattr(queue_item, 'toggle_pause'): queue_item.toggle_pause()
            
            if is_pausing:
                self.pause_all_btn.setText(helpers.BTN_RESUME_ALL)
                self.pause_all_btn.setObjectName("primary")
            else:
                self.pause_all_btn.setText(helpers.BTN_PAUSE_ALL)
                self.pause_all_btn.setObjectName("") 
            self.pause_all_btn.style().polish(self.pause_all_btn)

        finally:
            self.is_queue_locked = False 
            if not is_pausing: self.manage_queue() 

    def cancel_all_downloads(self):
        self.is_queue_locked = True 
        try:
            for i in reversed(range(self.queue_layout.count())):
                item = self.queue_layout.itemAt(i)
                if item and item.widget():
                    queue_item = item.widget()
                    if hasattr(queue_item, 'state') and queue_item.state not in ["completed", "cancelled"]:
                        if hasattr(queue_item, 'cancel_action'): queue_item.cancel_action()
            
            self.pause_all_btn.setText(helpers.BTN_PAUSE_ALL)
            self.pause_all_btn.setObjectName("")
            self.pause_all_btn.style().polish(self.pause_all_btn)
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
                    if hasattr(queue_item, 'state') and queue_item.state in ["completed", "error", "cancelled"]:
                        self.queue_layout.removeWidget(queue_item)
                        queue_item.deleteLater()
        finally:
            self.is_queue_locked = False
            self.manage_queue()

    def update_total_speed(self):
        try:
            total_speed = 0
            for i in range(self.queue_layout.count()):
                item = self.queue_layout.itemAt(i)
                if item and item.widget() and getattr(item.widget(), 'is_downloading', False):
                    if hasattr(item.widget(), 'dl_thread'): total_speed += getattr(item.widget().dl_thread, 'current_speed_bytes', 0)
            
            if total_speed > 1024 * 1024: self.total_speed_label.setText(helpers.LBL_TOTAL_SPEED + f"{total_speed / (1024 * 1024):.2f} MB/s")
            elif total_speed > 0: self.total_speed_label.setText(helpers.LBL_TOTAL_SPEED + f"{total_speed / 1024:.2f} KB/s")
            else: self.total_speed_label.setText(helpers.LBL_TOTAL_SPEED + "0 KB/s")
        except Exception:
            pass

    def update_placeholder_visibility(self):
        has_widgets = False
        for i in range(self.queue_layout.count()):
            item = self.queue_layout.itemAt(i)
            if item and item.widget():
                has_widgets = True
                break
        
        if has_widgets:
            self.placeholder_widget.hide()
            self.queue_area.show()
        else:
            self.placeholder_widget.show()
            self.queue_area.hide()

    def refresh_theme_icons(self):
        self.ph_icon.setPixmap(helpers.get_theme_icon("download.svg", 80).pixmap(80, 80))
        for i in range(self.queue_layout.count()):
            item = self.queue_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if hasattr(widget, 'refresh_theme_icons'):
                    widget.refresh_theme_icons()
