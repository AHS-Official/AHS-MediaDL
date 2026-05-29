import os
import sys
import glob
import subprocess
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QProgressBar
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QPainter, QColor
from utils.helpers import get_colored_icon, get_current_theme_color
from utils.locales import tr
from gui.components.common import ResponsiveImage, ElidedLabel

class DownloadCard(QFrame):

    def __init__(self, title, thumbnail_pixmap, save_path=""):
        super().__init__()
        self.save_path = save_path
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.setMinimumHeight(110)
        layout = QHBoxLayout(self)
        self.thumb_label = QLabel()
        if thumbnail_pixmap:
            scaled_thumb = thumbnail_pixmap.scaled(120, 70, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.thumb_label.setPixmap(scaled_thumb)
        self.thumb_label.setMinimumWidth(120)
        self.thumb_label.setMaximumWidth(150)
        layout.addWidget(self.thumb_label)
        details_layout = QVBoxLayout()
        top_row_layout = QHBoxLayout()
        self.title_label = ElidedLabel(title) 
        self.title_label.setToolTip(title) 
        card_font = self.title_label.font()
        card_font.setBold(True)
        card_font.setPointSize(card_font.pointSize() + 1)
        self.title_label.setFont(card_font)
        top_row_layout.addWidget(self.title_label)
        top_row_layout.setStretch(0, 1)
        self.btn_pause = self.create_icon_button("assets/icons/pause.svg", tr("tooltip_pause", "Pause"))
        self.btn_cancel = self.create_icon_button("assets/icons/cancel.svg", tr("tooltip_cancel", "Cancel"))
        self.btn_reload = self.create_icon_button("assets/icons/restart.svg", tr("tooltip_reload", "Reload"))
        self.btn_open = self.create_icon_button("assets/icons/folder-open.svg", tr("tooltip_open_folder", "Open Folder"))
        self.btn_reload.hide()
        self.btn_open.hide()
        top_row_layout.addWidget(self.btn_pause)
        top_row_layout.addWidget(self.btn_cancel)
        top_row_layout.addWidget(self.btn_reload)
        top_row_layout.addWidget(self.btn_open)
        details_layout.addLayout(top_row_layout)
        self.p_bar = QProgressBar()
        self.p_bar.setMinimumHeight(15)
        self.p_bar.setValue(0)
        details_layout.addWidget(self.p_bar)
        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(6)
        self.status_icon_lbl = QLabel()
        self.status_icon_lbl.setFixedSize(16, 16)
        self.status_icon_lbl.hide()
        self.status_label = ElidedLabel(tr("status_waiting_queue", "Waiting in queue..."))
        status_font = self.status_label.font()
        status_font.setPointSize(status_font.pointSize() - 1)
        self.status_label.setFont(status_font)
        status_layout.addWidget(self.status_icon_lbl)
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        details_layout.addLayout(status_layout)
        layout.addLayout(details_layout)
        layout.setStretch(1, 1)
        self.btn_cancel.clicked.connect(self.action_cancel)
        self.btn_pause.clicked.connect(self.action_pause_resume)
        self.btn_open.clicked.connect(self.action_open_folder)

    def create_icon_button(self, icon_path, tooltip):
        btn = QPushButton()
        icon = get_colored_icon(icon_path, get_current_theme_color())
        btn.setIcon(icon)
        btn.setIconSize(QSize(18, 18))
        btn.setToolTip(tooltip)
        btn.setFixedSize(32, 32)
        btn.setFlat(True) 
        btn.setStyleSheet("""
            QPushButton { border-radius: 6px; border: none; background: transparent; }
            QPushButton:hover { background-color: rgba(128, 128, 128, 0.2); }
        """)
        return btn

    def update_progress(self, val):
        self.p_bar.setValue(val)

    def update_status(self, msg):
        icon_path = None
        clean_msg = msg
        if "⏸️" in msg or "Paused" in msg or "مؤقتاً" in msg:
            icon_path = "assets/icons/pause.svg"
            clean_msg = msg.replace("⏸️", "").strip()
        elif "⏳" in msg or "Downloading" in msg or "تحميل" in msg or "Resuming" in msg or "استئناف" in msg or "Starting" in msg or "بدء" in msg:
            if "Resuming" in msg or "استئناف" in msg:
                icon_path = "assets/icons/restart.svg"
            elif "Starting" in msg or "بدء" in msg:
                icon_path = "assets/icons/rocket.svg"
            else:
                icon_path = "assets/icons/hourglass.svg"
            clean_msg = msg.replace("⏳", "").strip()
        elif "⚙️" in msg or "Processing" in msg or "معالجة" in msg:
            icon_path = "assets/icons/settings.svg"
            clean_msg = msg.replace("⚙️", "").strip()
        elif "🔍" in msg or "Inspecting" in msg or "فحص" in msg:
            icon_path = "assets/icons/search-lens.svg"
            clean_msg = msg.replace("🔍", "").strip()
        elif "✅" in msg or "Done" in msg or "اكتمل" in msg:
            icon_path = "assets/icons/check.svg"
            clean_msg = msg.replace("✅", "").strip()
        elif "❌" in msg or "Canceled" in msg or "إلغاء" in msg or "خطأ" in msg or "Error" in msg:
            icon_path = "assets/icons/cancel.svg"
            clean_msg = msg.replace("❌", "").strip()
        self.current_status_icon_path = icon_path
        if icon_path:
            self.status_icon_lbl.setPixmap(get_colored_icon(icon_path, get_current_theme_color()).pixmap(14, 14))
            self.status_icon_lbl.show()
        else:
            self.status_icon_lbl.hide()
        self.status_label.setText(clean_msg)
        if "✅" in msg or "Done" in msg or "اكتمل" in msg:
            self.btn_pause.hide()
            self.btn_cancel.hide()
            self.btn_reload.hide()
            self.btn_open.show()
            try:
                main_win = self.window()
                if hasattr(main_win, 'page_history'):
                    size_bytes = os.path.getsize(self.save_path) if os.path.exists(self.save_path) else 0
                    mb = size_bytes / (1024 * 1024)
                    size_str = f"{size_bytes / 1024:.1f} KB" if mb < 1 else f"{mb:.1f} MB"
                    url = getattr(self, 'url', 'N/A')
                    media_type = getattr(self, 'media_type', 'video')
                    duration = getattr(self, 'duration', '00:00')
                    main_win.page_history.add_to_history(self.title_label._full_text, duration, size_str, url, media_type)
                    if hasattr(main_win, 'show_notification'):
                        main_win.show_notification(
                            tr("status_done", "Download Completed"),
                            self.title_label._full_text,
                            self.thumb_label.pixmap()
                        )
            except Exception:
                pass
        elif "❌" in msg or "Error" in msg or "خطأ" in msg or "Canceled" in msg:
            self.btn_pause.hide()
            self.btn_cancel.hide()
            self.btn_reload.show()

    def update_icon_colors(self, icon_color):
        self.btn_pause.setIcon(get_colored_icon("assets/icons/pause.svg" if self.btn_pause.toolTip() == tr("tooltip_pause", "Pause") else "assets/icons/play.svg", icon_color))
        self.btn_cancel.setIcon(get_colored_icon("assets/icons/cancel.svg", icon_color))
        self.btn_reload.setIcon(get_colored_icon("assets/icons/restart.svg", icon_color))
        self.btn_open.setIcon(get_colored_icon("assets/icons/folder-open.svg", icon_color))
        if getattr(self, 'current_status_icon_path', None):
            self.status_icon_lbl.setPixmap(get_colored_icon(self.current_status_icon_path, icon_color).pixmap(14, 14))

    def action_cancel(self):
        self.status_label.setText(tr("status_cancelled", "❌ Canceled"))
        self.btn_pause.hide()
        self.btn_cancel.hide()
        self.btn_reload.show()
        if hasattr(self, 'worker') and self.worker:
            self.worker.cancel()

    def action_pause_resume(self):
        icon_color = get_current_theme_color()
        if self.btn_pause.toolTip() == tr("tooltip_pause", "Pause"):
            self.btn_pause.setIcon(get_colored_icon("assets/icons/play.svg", icon_color))
            self.btn_pause.setToolTip(tr("tooltip_resume", "Resume"))
            self.status_label.setText(tr("status_paused", "⏸️ Paused"))
            if hasattr(self, 'worker') and self.worker:
                self.worker.pause()
        else:
            self.btn_pause.setIcon(get_colored_icon("assets/icons/pause.svg", icon_color))
            self.btn_pause.setToolTip(tr("tooltip_pause", "Pause"))
            self.status_label.setText(tr("status_resuming", "⏳ Resuming..."))
            if hasattr(self, 'worker') and self.worker:
                self.worker.resume()

    def action_open_folder(self):
        path = os.path.normpath(self.save_path)
        folder_path = os.path.dirname(path)
        base_name = os.path.splitext(path)[0]
        possible_files = glob.glob(f"{base_name}.*")
        if sys.platform == 'win32':
            if possible_files:
                subprocess.Popen(f'explorer /select,"{possible_files[0]}"')
            elif os.path.exists(folder_path):
                os.startfile(folder_path)
        elif sys.platform == 'linux': 
            if os.path.exists(folder_path):
                subprocess.Popen(['xdg-open', folder_path])
        else:
            self.status_label.setText("❌ File deleted or moved!")

    def set_worker(self, worker):
        self.worker = worker

    def set_save_path(self, path):
        self.save_path = path

class PlaylistThumbnail(ResponsiveImage):
    clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.video_count = 0

    def set_count(self, count):
        self.video_count = count
        if count > 0:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.video_count > 0:
            self.clicked.emit()
        super().mousePressEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event) 
        if self.video_count > 0 and hasattr(self, '_pixmap') and self._pixmap:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            scaled_size = self._pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio).size()
            x = (self.width() - scaled_size.width()) // 2
            y = (self.height() - scaled_size.height()) // 2
            box_w = 120
            box_h = 35
            painter.fillRect(x, y + scaled_size.height() - box_h, box_w, box_h, QColor(0, 0, 0, 180)) 
            painter.setPen(Qt.GlobalColor.white)
            font = painter.font()
            font.setBold(True)
            font.setPointSize(font.pointSize() + 1)
            painter.setFont(font)
            painter.drawText(x, y + scaled_size.height() - box_h, box_w, box_h, Qt.AlignmentFlag.AlignCenter, f"▶ {self.video_count} Videos")

class HistoryCard(QFrame):

    def __init__(self, title, url, media_type, date_str=""):
        super().__init__()
        self.media_type = media_type
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.setMinimumHeight(75)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        self.icon_lbl = QLabel()
        self.icon_lbl.setFixedSize(24, 24)
        self.icon_lbl.setStyleSheet("background: transparent;")
        icon_file = "assets/icons/video.svg" if media_type == "video" else "assets/icons/music.svg"
        pixmap = get_colored_icon(icon_file, get_current_theme_color()).pixmap(QSize(24, 24))
        self.icon_lbl.setPixmap(pixmap)
        layout.addWidget(self.icon_lbl)
        details_layout = QVBoxLayout()
        details_layout.setSpacing(4)
        self.title_label = ElidedLabel(title)
        font = self.title_label.font()
        font.setBold(True)
        self.title_label.setFont(font)
        details_layout.addWidget(self.title_label)
        sub_layout = QHBoxLayout()
        info_text = f"{tr('download_date_lbl')}: {date_str}" if date_str else ""
        info_lbl = QLabel(info_text)
        info_lbl.setStyleSheet("color: gray; font-size: 11px;")
        url_lbl = QLabel()
        url_lbl.setText(f'<a href="{url}" style="color: #6b9fe4; text-decoration: none;">{tr("source_link")}</a>')
        url_lbl.setOpenExternalLinks(True)
        url_lbl.setStyleSheet("font-size: 11px;")
        sub_layout.addWidget(info_lbl)
        sub_layout.addStretch()
        sub_layout.addWidget(url_lbl)
        details_layout.addLayout(sub_layout)
        layout.addLayout(details_layout)
        layout.setStretch(1, 1)

    def update_icon_colors(self, icon_color):
        icon_file = "assets/icons/video.svg" if getattr(self, 'media_type', 'video') == "video" else "assets/icons/music.svg"
        pixmap = get_colored_icon(icon_file, icon_color).pixmap(QSize(24, 24))
        self.icon_lbl.setPixmap(pixmap)
