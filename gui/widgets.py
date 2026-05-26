"""
Reusable GUI widgets for AHS-MediaDL.
Contains: ToastNotification, DownloadQueueItem, HistoryCard, format_size()
"""
import os
import sys
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QLabel, QProgressBar, QPushButton, QFrame, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize, QUrl
from PyQt6.QtGui import QIcon, QPixmap, QDesktopServices
from core.downloader import DownloadThread
from data.settings import app_config
from utils import helpers


def format_size(bytes_val):
    """Format bytes into human-readable size string."""
    if not bytes_val or bytes_val <= 0:
        return "0.0 MB"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} PB"


# ──────────────────────────────────────────────
#  Toast Notification Widget
# ──────────────────────────────────────────────

class ToastNotification(QFrame):
    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.setObjectName("GlowCard")
        # Floating alert style
        self.setStyleSheet("""
            QFrame#GlowCard {
                background-color: rgba(229, 192, 123, 0.95);
                border: 2px solid #e5c07b;
                border-radius: 8px;
            }
            QLabel {
                color: #1a1a2e;
                font-weight: bold;
                font-size: 10pt;
                background-color: transparent;
            }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 8, 15, 8)
        
        self.label = QLabel(text)
        layout.addWidget(self.label)
        
        self.adjustSize()
        
        # Self-destruct after 4 seconds
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.fade_out)
        self.timer.start(4000)
        
    def fade_out(self):
        self.deleteLater()


# ──────────────────────────────────────────────
#  History Card Widget
# ──────────────────────────────────────────────

class HistoryCard(QFrame):
    def __init__(self, title, date, url, media_type="video", parent=None):
        super().__init__(parent)
        self.url = url
        self.setObjectName("GlowCard")
        self.setFixedHeight(95)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(helpers.HISTORY_CLICK_TIP)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(6)
        
        # Title
        self.title_label = QLabel(title)
        self.title_label.setObjectName("heading")
        self.title_label.setStyleSheet("font-weight: 700; font-size: 11pt; color: #7c6af7;")
        self.title_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(self.title_label)
        
        # Meta Row: [ Type Icon | Date | URL ]
        meta_layout = QHBoxLayout()
        meta_layout.setSpacing(6)
        
        self.type_icon = QLabel()
        self.media_type = media_type
        icon_name = "video.svg" if media_type == "video" else "music.svg"
        self.type_icon.setPixmap(helpers.get_theme_icon(icon_name, 14).pixmap(14, 14))
        
        date_icon = QLabel()
        date_icon.setPixmap(helpers.get_theme_icon("calendar.svg", 14).pixmap(14, 14))
        date_text = QLabel(date)
        date_text.setObjectName("hint")
        
        url_lbl = QLabel(url)
        url_lbl.setObjectName("hint")
        url_lbl.setStyleSheet("color: #61afef; text-decoration: underline;")
        
        meta_layout.addWidget(self.type_icon)
        meta_layout.addSpacing(10)
        meta_layout.addWidget(date_icon)
        meta_layout.addWidget(date_text)
        meta_layout.addSpacing(10)
        meta_layout.addWidget(url_lbl, stretch=1)
        
        layout.addLayout(meta_layout)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            QDesktopServices.openUrl(QUrl(self.url))


# ──────────────────────────────────────────────
#  Download Queue Item Widget
# ──────────────────────────────────────────────

class DownloadQueueItem(QFrame):
    download_completed_signal = pyqtSignal()

    def __init__(self, url, format_id, title, sub_langs=None, subs_only=False, embed_subs=False, save_dir=None, thumb_data=None):
        super().__init__()
        self.url = url
        self.format_id = format_id
        self.title = title
        self.sub_langs = sub_langs or []
        self.subs_only = subs_only
        self.embed_subs = embed_subs 
        self.save_dir = save_dir
        self.thumb_data = thumb_data
        
        self.last_downloaded_bytes = 0
        self.is_downloading = False 
        self.state = "waiting" 
        
        # Load Vector SVG Icons
        self.play_icon = helpers.get_theme_icon("play.svg")
        self.pause_icon = helpers.get_theme_icon("pause.svg")
        self.cancel_icon = helpers.get_theme_icon("cancel.svg")
        
        self.init_ui()
        
        if app_config.get("data_saver", False):
            self.state = "paused" 
            self.status_label.setText(helpers.Q_PAUSED_DATA)
            self.pause_btn.setVisible(True)
            self.pause_btn.setIcon(self.play_icon)
            self.pause_btn.setToolTip(helpers.BTN_START)
        else:
            self.status_label.setText(helpers.Q_WAITING) 
            self.pause_btn.setVisible(True)
            self.pause_btn.setIcon(self.pause_icon)
            self.pause_btn.setToolTip(helpers.BTN_PAUSE)

    def init_ui(self):
        self.setObjectName("QueueItem")
        self.setFixedHeight(120) # Height adjusted for modern card spacing

        main_h_layout = QHBoxLayout(self) 
        main_h_layout.setContentsMargins(12, 12, 12, 12) 
        main_h_layout.setSpacing(16)
        
        # Rounded Thumbnail
        self.thumb_img_label = QLabel()
        self.thumb_img_label.setFixedSize(120, 67)
        self.thumb_img_label.setStyleSheet("border-radius: 8px; background-color: rgba(0,0,0,0.1);")
        self.thumb_img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        has_thumb = False
        if hasattr(self, 'thumb_data') and self.thumb_data:
            pixmap = QPixmap()
            if pixmap.loadFromData(self.thumb_data):
                self.thumb_img_label.setPixmap(pixmap.scaled(120, 67, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation))
                has_thumb = True
        
        if not has_thumb:
            self.thumb_img_label.hide()
            
        main_h_layout.addWidget(self.thumb_img_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        info_v_layout = QVBoxLayout()
        info_v_layout.setSpacing(4) 
        info_v_layout.setContentsMargins(0, 0, 0, 0)
        
        max_chars = 55
        display_title = self.title if len(self.title) <= max_chars else self.title[:52] + "..."
        
        self.title_label = QLabel(display_title)
        self.title_label.setToolTip(self.title)
        self.title_label.setObjectName("heading")
        self.title_label.setStyleSheet("font-weight: 600; font-size: 11pt;")
        info_v_layout.addWidget(self.title_label)
        
        # Controls Row (above progress bar)
        self.controls_row_layout = QHBoxLayout()
        self.controls_row_layout.setContentsMargins(0, 0, 0, 0)
        self.controls_row_layout.addStretch()
        
        # Sleek, Icon-Based Control Buttons powered by SVGs
        self.pause_btn = QPushButton()
        self.pause_btn.setFixedSize(32, 32)
        self.pause_btn.setIconSize(QSize(18, 18))
        self.pause_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pause_btn.clicked.connect(self.toggle_pause)
        self.controls_row_layout.addWidget(self.pause_btn)

        self.cancel_btn = QPushButton()
        self.cancel_btn.setObjectName("danger")
        self.cancel_btn.setFixedSize(32, 32)
        self.cancel_btn.setIcon(self.cancel_icon)
        self.cancel_btn.setIconSize(QSize(18, 18))
        self.cancel_btn.setToolTip(helpers.BTN_CANCEL)
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.cancel_action)
        self.controls_row_layout.addWidget(self.cancel_btn)

        # Smart Open Folder Button (Hidden initially)
        self.open_folder_btn = QPushButton()
        self.open_folder_btn.setFixedSize(32, 32)
        self.open_folder_btn.setIcon(helpers.get_theme_icon("folder-open.svg"))
        self.open_folder_btn.setIconSize(QSize(18, 18))
        self.open_folder_btn.setToolTip(helpers.BTN_OPEN_FOLDER)
        self.open_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_folder_btn.clicked.connect(self.open_folder)
        self.open_folder_btn.hide()
        self.controls_row_layout.addWidget(self.open_folder_btn)
        
        info_v_layout.addLayout(self.controls_row_layout)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6) 
        self.progress_bar.setTextVisible(False)
        info_v_layout.addWidget(self.progress_bar)
        
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        self.status_label = QLabel(helpers.Q_WAITING)
        self.status_label.setObjectName("hint")
        bottom_layout.addWidget(self.status_label)
        bottom_layout.addStretch()
        
        info_v_layout.addLayout(bottom_layout)
        main_h_layout.addLayout(info_v_layout, stretch=1) 

    def start_download(self):
        self.is_downloading = True
        self.state = "downloading" 
        self.pause_btn.setVisible(True) 
        self.pause_btn.setIcon(self.pause_icon)
        self.pause_btn.setToolTip(helpers.BTN_PAUSE)
        self.status_label.setText(helpers.Q_WAITING)
        
        self.dl_thread = DownloadThread(self.url, self.format_id, self.sub_langs, self.subs_only, self.embed_subs, self.save_dir)
        self.dl_thread.progress_update.connect(self.update_progress)
        self.dl_thread.status_update.connect(self.update_status)
        self.dl_thread.finished.connect(self.download_finished)
        self.dl_thread.error.connect(self.download_error)
        self.dl_thread.start()

    def update_progress(self, percent, downloaded, total, speed, eta):
        self.progress_bar.setValue(percent)
        self.last_downloaded_bytes = downloaded
        
        dl_str = format_size(downloaded)
        total_str = format_size(total)
        
        # Display advanced progress metrics next to percentage: [ Size | Speed | ETA ]
        progress_text = f"Downloading {percent}%  |  {dl_str} / {total_str}  |  {speed}  |  ETA: {eta}"
        self.status_label.setText(progress_text)

    def update_status(self, status_msg):
        self.status_label.setText(status_msg)

    def download_finished(self):
        if getattr(self, 'state', '') in ["paused", "cancelled", "error"]:
            return 
            
        self.state = "completed" 
        self.status_label.setText(helpers.Q_COMPLETED)
        
        self.pause_btn.hide()
        self.cancel_btn.hide()
        self.open_folder_btn.show()
        
        # Auto-Log Download to History file!
        is_audio = "mp3" in self.format_id.lower() or "m4a" in self.format_id.lower()
        media_type = "audio" if is_audio else "video"
        
        from gui.pages.history_page import add_to_history
        add_to_history(self.title, self.url, media_type)
        
        # If history page is mounted in main window, reload it!
        parent = self.parentWidget()
        while parent:
            if hasattr(parent, 'history_page'):
                getattr(parent, 'history_page').reload_history()
                break
            parent = parent.parentWidget()
            
        # Trigger native system notification if notifications are enabled
        if app_config.get("notifications", True):
            helpers.send_system_notification(
                title=helpers.APP_TITLE,
                message=f"{helpers.Q_COMPLETED}: {self.title}"
            )
            
        self.is_downloading = False
        self.download_completed_signal.emit() 

    def download_error(self, error_msg):
        if error_msg == "Cancelled" or getattr(self, 'state', '') in ["paused", "cancelled", "completed"]: 
            return 
            
        self.state = "error" 
        self.status_label.setText(f"Error: {error_msg}")
        self.is_downloading = False
        
        # Fallback play icon for start/force retries
        self.pause_btn.setIcon(self.play_icon)
        self.pause_btn.setToolTip(helpers.BTN_FORCE if "Skipped:" in error_msg else helpers.BTN_START)
        
        if "Skipped:" in error_msg:
            try: self.pause_btn.clicked.disconnect()
            except: pass
            self.pause_btn.clicked.connect(self.force_download)
        
        self.download_completed_signal.emit()

    def toggle_pause(self):
        state = getattr(self, 'state', '')
        
        if state in ["downloading", "waiting"]: 
            self.state = "paused"
            self.pause_btn.setIcon(self.play_icon)
            self.pause_btn.setToolTip(helpers.BTN_RESUME)
            self.status_label.setText(helpers.Q_PAUSED_DATA)
            
            if hasattr(self, 'dl_thread') and self.dl_thread:
                self.dl_thread.cancel_download()
                if self.dl_thread.isRunning():
                    self.dl_thread.terminate()
                    
            self.is_downloading = False
            self.download_completed_signal.emit() 
                
        elif state == "paused":
            self.state = "waiting"
            self.pause_btn.setIcon(self.pause_icon)
            self.pause_btn.setToolTip(helpers.BTN_PAUSE)
            self.status_label.setText(helpers.Q_WAITING)
            
            parent = self.parentWidget()
            while parent:
                if hasattr(parent, 'manage_queue'):
                    parent.manage_queue()
                    break
                parent = parent.parentWidget()

    def cancel_action(self):
        was_downloading = (getattr(self, 'state', '') == "downloading") 
        
        self.state = "cancelled" 
        self.cancel_btn.setEnabled(False)
        self.pause_btn.hide()
        
        self.status_label.setText(helpers.BTN_CANCEL)
        
        if hasattr(self, 'dl_thread') and self.dl_thread:
            self.dl_thread.cancel_download()
            if self.dl_thread.isRunning():
                self.dl_thread.terminate() 
                
        self.is_downloading = False
        if was_downloading: 
            self.download_completed_signal.emit()

    def force_download(self):
        # Reset and force
        try: self.pause_btn.clicked.disconnect()
        except: pass
        self.pause_btn.clicked.connect(self.toggle_pause)
        self.start_download()

    def open_folder(self):
        import subprocess
        path = self.save_dir or app_config.get("save_path", os.path.expanduser("~"))
        try:
            if os.name == 'nt':
                os.startfile(path)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', path])
            else:
                subprocess.Popen(['xdg-open', path])
        except Exception:
            pass

    def refresh_theme_icons(self):
        self.play_icon = helpers.get_theme_icon("play.svg")
        self.pause_icon = helpers.get_theme_icon("pause.svg")
        self.cancel_icon = helpers.get_theme_icon("cancel.svg")
        
        # Refresh the buttons
        state = getattr(self, 'state', '')
        if state == "paused":
            self.pause_btn.setIcon(self.play_icon)
        elif state in ["downloading", "waiting"]:
            self.pause_btn.setIcon(self.pause_icon)
            
        if state != "completed":
            self.cancel_btn.setIcon(self.cancel_icon)
            
        # Refresh the smart open folder button
        self.open_folder_btn.setIcon(helpers.get_theme_icon("folder-open.svg"))
