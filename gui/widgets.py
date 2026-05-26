import os
import sys
import glob
import subprocess
from PyQt6.QtWidgets import (QLabel, QFrame, QHBoxLayout, QVBoxLayout, 
                             QPushButton, QProgressBar, QStyle, QWidget)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QIcon
from utils.helpers import resource_path, get_colored_icon, get_current_theme_color
from utils.locales import tr

class ResponsiveImage(QLabel):
    def __init__(self):
        super().__init__()
        self._pixmap = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(self.sizePolicy().Policy.Expanding, self.sizePolicy().Policy.Expanding)
        self.setMinimumHeight(120)

    def sizeHint(self):
        return QSize(120, 120)

    def setPixmap(self, pixmap):
        self._pixmap = pixmap
        self.update_image()

    def resizeEvent(self, event):
        if self._pixmap:
            self.update_image()
        super().resizeEvent(event)

    def update_image(self):
        if self._pixmap and not self.size().isEmpty():
            scaled = self._pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            super().setPixmap(scaled)

class ElidedLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._full_text = text
        self.setToolTip(text)
        self.setSizePolicy(self.sizePolicy().Policy.Expanding, self.sizePolicy().Policy.Preferred)

    def setText(self, text):
        self._full_text = text
        self.setToolTip(text)
        super().setText(text)

    def sizeHint(self):
        metrics = self.fontMetrics()
        return metrics.size(Qt.TextFlag.TextSingleLine, self._full_text)

    def minimumSizeHint(self):
        metrics = self.fontMetrics()
        return QSize(metrics.horizontalAdvance("..."), metrics.height())

    def paintEvent(self, event):
        painter = QPainter(self)
        metrics = self.fontMetrics()
        elided = metrics.elidedText(self._full_text, Qt.TextElideMode.ElideRight, self.width())
        painter.drawText(self.rect(), self.alignment(), elided)

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

        self.btn_pause = self.create_icon_button("assets/icons/pause.svg", "Pause")
        self.btn_cancel = self.create_icon_button("assets/icons/cancel.svg", "Cancel")
        self.btn_reload = self.create_icon_button("assets/icons/restart.svg", "Reload")
        self.btn_open = self.create_icon_button("assets/icons/folder-open.svg", "Open Folder")
        
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

        self.status_label = ElidedLabel("Waiting...")
        status_font = self.status_label.font()
        status_font.setPointSize(status_font.pointSize() - 1)
        self.status_label.setFont(status_font)
        details_layout.addWidget(self.status_label)

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
        self.status_label.setText(msg)
        if "✅" in msg:
            self.btn_pause.hide()
            self.btn_cancel.hide()
            self.btn_reload.hide()
            self.btn_open.show()
            
            # 💡 حفظ السجل تلقائياً عند اكتمال التنزيل بنجاح
            try:
                main_win = self.window()
                if hasattr(main_win, 'page_history'):
                    # حساب المساحة الفعلية للملف الحالي من الهارد ديسك
                    size_bytes = os.path.getsize(self.save_path) if os.path.exists(self.save_path) else 0
                    mb = size_bytes / (1024 * 1024)
                    size_str = f"{size_bytes / 1024:.1f} KB" if mb < 1 else f"{mb:.1f} MB"
                    
                    url = getattr(self, 'url', 'N/A')
                    media_type = getattr(self, 'media_type', 'video')
                    duration = getattr(self, 'duration', '00:00')
                    
                    main_win.page_history.add_to_history(self.title_label._full_text, duration, size_str, url, media_type)
                    
                    # 🔔 إظهار إشعار اكتمال التحميل
                    if hasattr(main_win, 'show_notification'):
                        main_win.show_notification(
                            tr("status_done", "Download Completed"),
                            self.title_label._full_text
                        )
            except Exception:
                pass

    def update_icon_colors(self, icon_color):
        self.btn_pause.setIcon(get_colored_icon("assets/icons/pause.svg" if self.btn_pause.toolTip() == "Pause" else "assets/icons/play.svg", icon_color))
        self.btn_cancel.setIcon(get_colored_icon("assets/icons/cancel.svg", icon_color))
        self.btn_reload.setIcon(get_colored_icon("assets/icons/restart.svg", icon_color))
        self.btn_open.setIcon(get_colored_icon("assets/icons/folder-open.svg", icon_color))

    def action_cancel(self):
        self.status_label.setText("❌ Canceled")
        self.btn_pause.hide()
        self.btn_cancel.hide()
        self.btn_reload.show()
        if hasattr(self, 'worker') and self.worker:
            self.worker.cancel()

    def action_pause_resume(self):
        icon_color = get_current_theme_color()
        if self.btn_pause.toolTip() == "Pause":
            self.btn_pause.setIcon(get_colored_icon("assets/icons/play.svg", icon_color))
            self.btn_pause.setToolTip("Resume")
            self.status_label.setText("⏸️ Paused")
            if hasattr(self, 'worker') and self.worker:
                self.worker.pause()
        else:
            self.btn_pause.setIcon(get_colored_icon("assets/icons/pause.svg", icon_color))
            self.btn_pause.setToolTip("Pause")
            self.status_label.setText("⏳ Resuming...")
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
        
        # أيقونة مخصصة حسب نوع الميديا (فيديو أو صوت)
        self.icon_lbl = QLabel()
        self.icon_lbl.setFixedSize(24, 24)
        self.icon_lbl.setStyleSheet("background: transparent;")
        icon_file = "assets/icons/video.svg" if media_type == "video" else "assets/icons/music.svg"
        pixmap = get_colored_icon(icon_file, get_current_theme_color()).pixmap(QSize(24, 24))
        self.icon_lbl.setPixmap(pixmap)
        layout.addWidget(self.icon_lbl)
        
        details_layout = QVBoxLayout()
        details_layout.setSpacing(4)
        
        # اسم الفيديو
        self.title_label = ElidedLabel(title)
        font = self.title_label.font()
        font.setBold(True)
        self.title_label.setFont(font)
        details_layout.addWidget(self.title_label)
        
        # السطر السفلي (التاريخ ورابط المصدر)
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

class EmptyStateWidget(QWidget):
    def __init__(self, icon_path, title, subtitle="", parent=None):
        super().__init__(parent)
        self.setSizePolicy(self.sizePolicy().Policy.Expanding, self.sizePolicy().Policy.Expanding)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 20, 40, 20)
        layout.setSpacing(16)
        
        layout.addStretch(1)
        
        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setFixedSize(120, 120)
        self.icon_label.setStyleSheet("background: transparent;")
        
        # Load colored icon dynamically
        pixmap = get_colored_icon(icon_path, get_current_theme_color()).pixmap(QSize(120, 120))
        self.icon_label.setPixmap(pixmap)
        layout.addWidget(self.icon_label, 0, Qt.AlignmentFlag.AlignCenter)
        
        self.title_label = QLabel(title)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setWordWrap(True)
        title_font = self.title_label.font()
        title_font.setBold(True)
        title_font.setPointSize(title_font.pointSize() + 3)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet("color: #94a3b8; background: transparent;")
        layout.addWidget(self.title_label)
        
        if subtitle:
            self.subtitle_label = QLabel(subtitle)
            self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.subtitle_label.setWordWrap(True)
            sub_font = self.subtitle_label.font()
            sub_font.setPointSize(sub_font.pointSize())
            self.subtitle_label.setFont(sub_font)
            self.subtitle_label.setStyleSheet("color: #64748b; background: transparent;")
            layout.addWidget(self.subtitle_label)
            
        layout.addStretch(1)

    def update_icon_color(self, icon_path, icon_color):
        pixmap = get_colored_icon(icon_path, icon_color).pixmap(QSize(120, 120))
        self.icon_label.setPixmap(pixmap)