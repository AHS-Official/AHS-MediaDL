import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QProgressBar, QPushButton, QFrame, QSizePolicy)
from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices, QPixmap, QCursor
from core.downloader import DownloadThread
from utils.settings import app_config, DEFAULT_DOWNLOAD_PATH
from utils import strings

try:
    from plyer import notification
except ImportError:
    notification = None

class SmartTitleLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self._full_text = text
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWordWrap(True)
        self.setStyleSheet("font-weight: 700; font-size: 14px; background: transparent;")
        if text:
            self.setToolTip(text)
            super().setText(text)

    def setText(self, text):
        self._full_text = text or ""
        self.setToolTip(self._full_text)
        super().setText(self._full_text)

class ClickableThumbnail(QLabel):
    double_clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor)) 
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
    def mouseDoubleClickEvent(self, event):
        self.double_clicked.emit()
        super().mouseDoubleClickEvent(event)

class DownloadQueueItem(QWidget):
    download_completed_signal = pyqtSignal()

    def __init__(self, url, format_id, title, sub_langs=None, subs_only=False, embed_subs=False, save_dir=None, thumb_data=None):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        
        self.url = url
        self.format_id = format_id
        self.title = title
        self.sub_langs = sub_langs or []
        self.subs_only = subs_only
        self.embed_subs = embed_subs 
        self.save_dir = save_dir
        self.thumb_data = thumb_data
        
        self.init_ui()
        self.is_downloading = False 
        self.state = "waiting" 
        
        if app_config.get("data_saver"):
            self.state = "paused" 
            self.set_status("متوقف (توفير بيانات)" if strings.is_ar else "Paused (Data Saver)", "#f59e0b", "rgba(245, 158, 11, 0.15)")
            self.start_btn.setVisible(False)
            self.pause_btn.setVisible(True)
            self.pause_btn.setText("▶️")
            self.pause_btn.setToolTip(strings.TOOLTIP_START)
        else:
            self.set_status(strings.STATUS_WAITING, "#9ca3af", "rgba(156, 163, 175, 0.12)")
            self.start_btn.setVisible(False)
            self.pause_btn.setVisible(True)
            self.pause_btn.setText("⏸️")
            self.pause_btn.setToolTip(strings.TOOLTIP_PAUSE)

    def init_ui(self):
        self.setObjectName("QueueCard")
        
        main_h_layout = QHBoxLayout(self) 
        main_h_layout.setContentsMargins(14, 14, 14, 14)
        main_h_layout.setSpacing(14)
        
        self.thumb_img_label = ClickableThumbnail()
        self.thumb_img_label.setFixedSize(110, 64) 
        self.thumb_img_label.setObjectName("Thumbnail")
        self.thumb_img_label.setToolTip("انقر مرتين لفتح المجلد" if strings.is_ar else "Double click to open folder")
        self.thumb_img_label.double_clicked.connect(self.open_folder) 
        
        if hasattr(self, 'thumb_data') and self.thumb_data:
            pixmap = QPixmap()
            if pixmap.loadFromData(self.thumb_data):
                self.thumb_img_label.setPixmap(pixmap.scaled(110, 64, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
        
        main_h_layout.addWidget(self.thumb_img_label, alignment=Qt.AlignmentFlag.AlignTop)
        
        info_v_layout = QVBoxLayout()
        info_v_layout.setSpacing(6)

        top_row_layout = QHBoxLayout()
        top_row_layout.setSpacing(8)
        
        self.title_label = SmartTitleLabel(self.title)
        self.title_label.setStyleSheet("font-weight: 700; font-size: 13px; background: transparent; border: none;")
        top_row_layout.addWidget(self.title_label, stretch=1)

        self.status_badge = QLabel()
        self.status_badge.setStyleSheet("font-size: 11px; font-weight: 700; border-radius: 6px; padding: 2px 8px; background: rgba(76, 117, 242, 0.15); color: #4c75f2;")
        top_row_layout.addWidget(self.status_badge)

        self.controls_layout = QHBoxLayout()
        self.controls_layout.setSpacing(4)
        
        btn_size = 30
        
        self.start_btn = QPushButton("▶️") 
        self.start_btn.setToolTip(strings.TOOLTIP_START)
        self.start_btn.setFixedSize(btn_size, btn_size)
        self.start_btn.setObjectName("icon_btn")
        self.start_btn.clicked.connect(self.start_download)
        
        self.pause_btn = QPushButton("⏸️") 
        self.pause_btn.setToolTip(strings.TOOLTIP_PAUSE)
        self.pause_btn.setFixedSize(btn_size, btn_size)
        self.pause_btn.setObjectName("icon_btn")
        self.pause_btn.hide()
        self.pause_btn.clicked.connect(self.toggle_pause)

        self.cancel_btn = QPushButton("❌") 
        self.cancel_btn.setToolTip(strings.TOOLTIP_CANCEL)
        self.cancel_btn.setFixedSize(btn_size, btn_size)
        self.cancel_btn.setObjectName("icon_btn")
        self.cancel_btn.clicked.connect(self.cancel_action)

        self.controls_layout.addWidget(self.start_btn)
        self.controls_layout.addWidget(self.pause_btn)
        self.controls_layout.addWidget(self.cancel_btn)
        top_row_layout.addLayout(self.controls_layout)
        info_v_layout.addLayout(top_row_layout)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        info_v_layout.addWidget(self.progress_bar)
        
        stats_layout = QHBoxLayout()
        stats_layout.setContentsMargins(0, 0, 0, 0)
        
        self.size_label = QLabel("-- / --")
        self.size_label.setStyleSheet("font-size: 11px; color: #9ca3af; font-weight: 600; background: transparent;")
        
        self.speed_label = QLabel("")
        self.speed_label.setStyleSheet("font-size: 11px; color: #9ca3af; font-weight: 600; background: transparent;")
        
        self.eta_label = QLabel("")
        self.eta_label.setStyleSheet("font-size: 11px; color: #9ca3af; font-weight: 600; background: transparent;")

        stats_layout.addWidget(self.size_label)
        stats_layout.addStretch()
        stats_layout.addWidget(self.speed_label)
        stats_layout.addSpacing(12)
        stats_layout.addWidget(self.eta_label)
        
        info_v_layout.addLayout(stats_layout)
        main_h_layout.addLayout(info_v_layout, stretch=1)

    def set_status(self, text, color, bg_color="rgba(76, 117, 242, 0.15)"):
        self.status_badge.setText(text)
        self.status_badge.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {color}; background-color: {bg_color}; border-radius: 6px; padding: 2px 8px;")

    def start_download(self):
        self.is_downloading = True
        self.state = "downloading"
        self.start_btn.setVisible(False)
        self.pause_btn.setVisible(True) 
        self.pause_btn.setText("⏸️")
        self.pause_btn.setToolTip(strings.TOOLTIP_PAUSE)
        self.set_status("جاري التحميل..." if strings.is_ar else "Downloading...", "#4c75f2", "rgba(76, 117, 242, 0.15)") 
        
        self.dl_thread = DownloadThread(
            url=self.url,
            format_id=self.format_id,
            title=self.title,
            sub_langs=self.sub_langs,
            subs_only=self.subs_only,
            embed_subs=self.embed_subs,
            save_dir=self.save_dir,
            thumb_data=self.thumb_data
        )
        self.dl_thread.progress_update.connect(self.update_progress)
        self.dl_thread.status_update.connect(self.update_status)
        self.dl_thread.finished.connect(self.download_finished)
        self.dl_thread.error.connect(self.download_error)
        self.dl_thread.start()

    def update_progress(self, value, speed="0 KB/s", eta="--:--", size_str=""):
        self.progress_bar.setValue(value)
        if size_str:
            self.size_label.setText(size_str)
        
        if getattr(self, 'state', '') == "downloading":
            self.speed_label.setText(f"🚀 {speed}")
            self.eta_label.setText(f"⏳ {eta}")
            self.speed_label.show()
            self.eta_label.show()

    def update_status(self, text):
        if self.state == "downloading":
            self.set_status(text, "#4c75f2", "rgba(76, 117, 242, 0.15)")

    def download_finished(self):
        if getattr(self, 'state', '') in ["paused", "cancelled", "error"]:
            return 
            
        self.state = "completed" 
        self.set_status("✅ مكتمل" if strings.is_ar else "✅ Completed", "#10b981", "rgba(16, 185, 129, 0.15)") 
        
        self.progress_bar.setValue(100)
        self.progress_bar.setStyleSheet("""
            QProgressBar { background-color: #2b2e38; border-radius: 3px; border: none; }
            QProgressBar::chunk { background-color: #10b981; border-radius: 3px; }
        """)
        
        self.speed_label.hide()
        self.eta_label.hide()
        
        self.pause_btn.hide()
        self.start_btn.hide()
        self.cancel_btn.setEnabled(True)
        self.cancel_btn.setText("📁") 
        self.cancel_btn.setToolTip(strings.TOOLTIP_FOLDER)
        self.cancel_btn.setObjectName("primary")
        
        try: self.cancel_btn.clicked.disconnect()
        except: pass
        self.cancel_btn.clicked.connect(self.open_folder)
        
        if app_config.get("notifications", True) and notification:
            try: notification.notify(title="Download Complete 📥", message=f"{self.title[:30]}...", app_name="AHS-MediaDL", timeout=5)
            except: pass
            
        self.is_downloading = False
        self.download_completed_signal.emit() 

    def open_folder(self):
        target_dir = self.save_dir if self.save_dir else (app_config.get("custom_path") if app_config.get("save_mode") == "custom" and app_config.get("custom_path") else DEFAULT_DOWNLOAD_PATH)
        QDesktopServices.openUrl(QUrl.fromLocalFile(target_dir))

    def download_error(self, error_msg):
        if error_msg == "Cancelled" or getattr(self, 'state', '') in ["paused", "cancelled", "completed"]: 
            return 
            
        self.state = "error" 
        self.set_status("خطأ" if strings.is_ar else "Error", "#ef4444", "rgba(239, 68, 68, 0.15)") 
        self.is_downloading = False
        self.pause_btn.hide()
        
        self.start_btn.setVisible(True)
        self.start_btn.setText("↻")
        self.start_btn.setToolTip("إعادة المحاولة" if strings.is_ar else "Retry")
        try: self.start_btn.clicked.disconnect()
        except: pass
        
        if "Skipped:" in error_msg:
            self.start_btn.clicked.connect(self.force_download)
        else:
            self.start_btn.clicked.connect(self.start_download)
        
        self.download_completed_signal.emit()

    def force_download(self):
        self.set_status("إجبار التحميل..." if strings.is_ar else "Forcing...", "#f59e0b", "rgba(245, 158, 11, 0.15)")
        app_config["allow_downgrade"] = True
        self.start_download()

    def toggle_pause(self):
        state = getattr(self, 'state', '')
        
        if state in ["downloading", "waiting"]:
            self.state = "paused"
            self.set_status("متوقف مؤقتاً" if strings.is_ar else "Paused", "#f59e0b", "rgba(245, 158, 11, 0.15)") 
            self.pause_btn.setText("▶️")
            self.pause_btn.setToolTip(strings.TOOLTIP_START)
            
            self.speed_label.hide()
            self.eta_label.hide()
            
            if hasattr(self, 'dl_thread') and self.dl_thread:
                self.dl_thread.cancel_download()
                    
            self.is_downloading = False
            self.download_completed_signal.emit() 
                
        elif state == "paused":
            self.state = "waiting"
            self.set_status(strings.STATUS_WAITING, "#9ca3af", "rgba(156, 163, 175, 0.12)")
            self.pause_btn.setText("⏸️")
            self.pause_btn.setToolTip(strings.TOOLTIP_PAUSE)
            
            parent = self.parentWidget()
            while parent:
                if hasattr(parent, 'manage_queue'):
                    parent.manage_queue()
                    break
                parent = parent.parentWidget() 

    def cancel_action(self):
        was_downloading = (getattr(self, 'state', '') == "downloading")
        self.state = "cancelled" 
        
        self.set_status(strings.STATUS_CANCELLED, "#ef4444", "rgba(239, 68, 68, 0.15)") 
        self.cancel_btn.setEnabled(False)
        self.start_btn.setVisible(False)
        self.pause_btn.hide()
        self.speed_label.hide()
        self.eta_label.hide()
        
        if hasattr(self, 'dl_thread') and self.dl_thread:
            self.dl_thread.cancel_download()
            self.dl_thread.wait(2000)
                
        self.is_downloading = False
        if was_downloading:
            self.download_completed_signal.emit()
        else:
            parent = self.parentWidget()
            while parent:
                if hasattr(parent, 'manage_queue'):
                    parent.manage_queue()
                    break
                parent = parent.parentWidget()