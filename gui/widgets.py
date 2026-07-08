from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton
from PyQt6.QtCore import Qt, QUrl, pyqtSignal, QEvent
from PyQt6.QtGui import QDesktopServices, QPixmap, QCursor
from core.downloader import DownloadThread
from utils.settings import app_config, DEFAULT_DOWNLOAD_PATH
from utils import strings
import os

try:
    from plyer import notification
except ImportError:
    notification = None

from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt

class SmartTitleLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self._full_text = text
        self.setToolTip(text)
        self.setStyleSheet("font-weight: bold; font-size: 13px;")
        
    def resizeEvent(self, event):
        super().resizeEvent(event)
        metrics = self.fontMetrics()
        elided = metrics.elidedText(self._full_text, Qt.TextElideMode.ElideRight, self.width() - 5)
        super().setText(elided)

class ClickableThumbnail(QLabel):
    double_clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor)) 
        
    def mouseDoubleClickEvent(self, event):
        self.double_clicked.emit()
        super().mouseDoubleClickEvent(event)

class DownloadQueueItem(QWidget):
    download_completed_signal = pyqtSignal()
    history_ready_signal = pyqtSignal(dict)
    def __init__(self, url, format_id, title, sub_langs=None, subs_only=False, embed_subs=False, save_dir=None, thumb_data=None, custom_metadata=None):
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
        self.custom_metadata = custom_metadata
        
        self.init_ui()
        self.is_downloading = False 
        self.state = "waiting" 
        
        if app_config.get("data_saver"):
            self.state = "paused" 
            self.set_status("متوقف (توفير بيانات)" if strings.is_ar else "Paused (Data Saver)", "#e67e22")
            self.start_btn.setVisible(False)
            self.pause_btn.setVisible(True)
            self.pause_btn.setText("▶️")
            self.pause_btn.setToolTip(strings.TOOLTIP_START)
        else:
            self.set_status(strings.STATUS_WAITING, "#888888")
            self.start_btn.setVisible(False)
            self.pause_btn.setVisible(True)
            self.pause_btn.setText("⏸️")
            self.pause_btn.setToolTip(strings.TOOLTIP_PAUSE)

    def init_ui(self):
        self.setObjectName("QueueCard")
        self.setStyleSheet("""
            #QueueCard {
                background-color: rgba(128, 128, 128, 0.05); 
                border-radius: 8px;
                border: 1px solid #7f8c8d; /* الإطار الظاهر */
                margin-bottom: 8px;
            }
            #QueueCard:hover {
                border: 1px solid #4d78cc; /* إطار أزرق عند الوقوف بالماوس */
                background-color: rgba(128, 128, 128, 0.09);
            }
        """)

        main_h_layout = QHBoxLayout(self) 
        main_h_layout.setContentsMargins(12, 12, 12, 12)
        main_h_layout.setSpacing(12)
        
        self.thumb_img_label = ClickableThumbnail()
        self.thumb_img_label.setFixedSize(120, 67) 
        self.thumb_img_label.setStyleSheet("background-color: transparent; border-radius: 4px;")
        self.thumb_img_label.setToolTip("انقر مرتين لفتح المجلد/الملف" if strings.is_ar else "Double click to open")
        self.thumb_img_label.double_clicked.connect(self.open_folder) 
        
        if hasattr(self, 'thumb_data') and self.thumb_data:
            pixmap = QPixmap()
            if pixmap.loadFromData(self.thumb_data):
                self.thumb_img_label.setPixmap(pixmap.scaled(120, 67, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation))
        
        main_h_layout.addWidget(self.thumb_img_label, alignment=Qt.AlignmentFlag.AlignTop)
        
        info_v_layout = QVBoxLayout()
        info_v_layout.setSpacing(6)

        top_row_layout = QHBoxLayout()
        
        self.title_label = SmartTitleLabel(self.title)
        self.title_label.setToolTip(self.title)
        self.title_label.setStyleSheet("font-weight: bold; font-size: 13px; background: transparent; border: none;")
        top_row_layout.addWidget(self.title_label, stretch=1)

        self.controls_layout = QHBoxLayout()
        self.controls_layout.setSpacing(5)
        
        btn_size = 32
        icon_btn_style = "padding: 0px; font-size: 14px; background: transparent;"
        
        self.start_btn = QPushButton("▶️") 
        self.start_btn.setToolTip(strings.TOOLTIP_START)
        self.start_btn.setFixedSize(btn_size, btn_size)
        self.start_btn.setObjectName("ghost")
        self.start_btn.setStyleSheet(icon_btn_style)
        self.start_btn.clicked.connect(self.start_download)
        
        self.pause_btn = QPushButton("⏸️") 
        self.pause_btn.setToolTip(strings.TOOLTIP_PAUSE)
        self.pause_btn.setFixedSize(btn_size, btn_size)
        self.pause_btn.setObjectName("ghost")
        self.pause_btn.setStyleSheet(icon_btn_style)
        self.pause_btn.hide()
        self.pause_btn.clicked.connect(self.toggle_pause)

        self.cancel_btn = QPushButton("❌") 
        self.cancel_btn.setToolTip(strings.TOOLTIP_CANCEL)
        self.cancel_btn.setFixedSize(btn_size, btn_size)
        self.cancel_btn.setObjectName("ghost")
        self.cancel_btn.setStyleSheet(icon_btn_style)
        self.cancel_btn.clicked.connect(self.cancel_action)

        self.controls_layout.addWidget(self.start_btn)
        self.controls_layout.addWidget(self.pause_btn)
        self.controls_layout.addWidget(self.cancel_btn)
        top_row_layout.addLayout(self.controls_layout)
        info_v_layout.addLayout(top_row_layout)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar { background-color: #ecf0f1; border-radius: 3px; border: none; }
            QProgressBar::chunk { background-color: #4d78cc; border-radius: 3px; }
        """)
        info_v_layout.addWidget(self.progress_bar)
        
        stats_layout = QHBoxLayout()
        
        self.status_label = QLabel()
        self.status_label.setStyleSheet("font-size: 11px; font-weight: bold; background: transparent; border: none;")
        
        self.size_label = QLabel("-- / --")
        self.size_label.setStyleSheet("font-size: 11px; color: #888; font-weight: bold; background: transparent; border: none;")
        
        self.speed_label = QLabel("")
        self.speed_label.setStyleSheet("font-size: 11px; color: #888; background: transparent; border: none;")
        
        self.eta_label = QLabel("")
        self.eta_label.setStyleSheet("font-size: 11px; color: #888; background: transparent; border: none;")

        stats_layout.addWidget(self.status_label)
        stats_layout.addSpacing(10)
        stats_layout.addWidget(self.size_label)
        stats_layout.addStretch()
        stats_layout.addWidget(self.speed_label)
        stats_layout.addSpacing(10)
        stats_layout.addWidget(self.eta_label)
        
        info_v_layout.addLayout(stats_layout)
        main_h_layout.addLayout(info_v_layout, stretch=1)

    def set_status(self, text, color):
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {color}; background: transparent; border: none;")

    def start_download(self):
        self.is_downloading = True
        self.state = "downloading"
        self.start_btn.setVisible(False)
        self.pause_btn.setVisible(True) 
        self.pause_btn.setText("⏸️")
        self.pause_btn.setToolTip(strings.TOOLTIP_PAUSE)
        self.set_status("جاري التحميل..." if strings.is_ar else "Downloading...", "#4d78cc") 
        
        self.dl_thread = DownloadThread(
            url=self.url,
            format_id=self.format_id,
            title=self.title,
            sub_langs=self.sub_langs,
            subs_only=self.subs_only,
            embed_subs=self.embed_subs,
            save_dir=self.save_dir,
            thumb_data=self.thumb_data,
            custom_metadata=self.custom_metadata
        )
        self.dl_thread.progress_update.connect(self.update_progress)
        self.dl_thread.status_update.connect(self.update_status)
        self.dl_thread.finished.connect(self.download_finished)
        self.dl_thread.error.connect(self.download_error)
        self.dl_thread.history_ready.connect(self.history_ready_signal.emit)
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
            self.set_status(text, "#4d78cc")

    def download_finished(self):
        if getattr(self, 'state', '') in ["paused", "cancelled", "error"]:
            return 
            
        self.state = "completed" 
        self.set_status("✅ مكتمل" if strings.is_ar else "✅ Completed", "#27ae60") 
        
        self.progress_bar.setValue(100)
        self.progress_bar.setStyleSheet("""
            QProgressBar { background-color: #ecf0f1; border-radius: 3px; border: none; }
            QProgressBar::chunk { background-color: #27ae60; border-radius: 3px; }
        """)
        
        self.speed_label.hide()
        self.eta_label.hide()
        
        self.pause_btn.hide()
        self.start_btn.hide()
        self.cancel_btn.setEnabled(True)
        self.cancel_btn.setText("📁") 
        self.cancel_btn.setToolTip(strings.TOOLTIP_FOLDER)
        self.cancel_btn.setObjectName("primary") 
        self.cancel_btn.setStyleSheet("padding: 0px; font-size: 14px;")
        
        try: self.cancel_btn.clicked.disconnect()
        except: pass
        self.cancel_btn.clicked.connect(self.open_folder)
        
        if app_config["notifications"] and notification:
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
        self.set_status(f"خطأ: {error_msg}", "#e74c3c") 
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
        self.set_status("إجبار التحميل..." if strings.is_ar else "Forcing...", "#e67e22")
        app_config["allow_downgrade"] = True
        self.start_download()

    def toggle_pause(self):
        state = getattr(self, 'state', '')
        
        if state in ["downloading", "waiting"]:
            self.state = "paused"
            self.set_status("متوقف مؤقتاً" if strings.is_ar else "Paused", "#e67e22") 
            self.pause_btn.setText("▶️")
            self.pause_btn.setToolTip(strings.TOOLTIP_START)
            
            self.speed_label.hide()
            self.eta_label.hide()
            
            if hasattr(self, 'dl_thread') and self.dl_thread:
                self.dl_thread.cancel_download()
                # تم إزالة terminate() نهائياً لحماية الذاكرة والملفات
                    
            self.is_downloading = False
            self.download_completed_signal.emit() 
                
        elif state == "paused":
            self.state = "waiting"
            self.set_status(strings.STATUS_WAITING, "#888888")
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
        
        self.set_status(strings.STATUS_CANCELLED, "#e74c3c") 
        self.cancel_btn.setEnabled(False)
        self.start_btn.setVisible(False)
        self.pause_btn.hide()
        self.speed_label.hide()
        self.eta_label.hide()
        
        if hasattr(self, 'dl_thread') and self.dl_thread:
            self.dl_thread.cancel_download()
            self.dl_thread.wait(2000) # نعطي الخيط فرصة دلالية لإغلاق الملفات بأمان 
                
        self.is_downloading = False
        if was_downloading:
            self.download_completed_signal.emit()