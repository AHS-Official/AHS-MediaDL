import os
import sys
import glob
import subprocess
from PyQt6.QtWidgets import (QLabel, QFrame, QHBoxLayout, QVBoxLayout, 
                             QPushButton, QProgressBar, QStyle)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPainter, QColor

class ResponsiveImage(QLabel):
    def __init__(self):
        super().__init__()
        self._pixmap = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(self.sizePolicy().Policy.Expanding, self.sizePolicy().Policy.Expanding)
        self.setMinimumHeight(120)

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

        self.btn_pause = self.create_icon_button(QStyle.StandardPixmap.SP_MediaPause, "Pause")
        self.btn_cancel = self.create_icon_button(QStyle.StandardPixmap.SP_DialogCancelButton, "Cancel")
        self.btn_reload = self.create_icon_button(QStyle.StandardPixmap.SP_BrowserReload, "Reload")
        self.btn_open = self.create_icon_button(QStyle.StandardPixmap.SP_DirOpenIcon, "Open Folder")
        
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

        self.status_label = QLabel("Waiting...")
        status_font = self.status_label.font()
        status_font.setPointSize(status_font.pointSize() - 1)
        self.status_label.setFont(status_font)
        details_layout.addWidget(self.status_label)

        layout.addLayout(details_layout)
        layout.setStretch(1, 1)

        self.btn_cancel.clicked.connect(self.action_cancel)
        self.btn_pause.clicked.connect(self.action_pause_resume)
        self.btn_open.clicked.connect(self.action_open_folder)

    def create_icon_button(self, standard_pixmap, tooltip):
        btn = QPushButton()
        icon = self.style().standardIcon(standard_pixmap)
        btn.setIcon(icon)
        btn.setToolTip(tooltip)
        btn.setFixedSize(32, 32)
        btn.setFlat(True) 
        btn.setStyleSheet("""
            QPushButton { border-radius: 4px; }
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

    def action_cancel(self):
        self.status_label.setText("❌ Canceled")
        self.btn_pause.hide()
        self.btn_cancel.hide()
        self.btn_reload.show()
        if hasattr(self, 'worker') and self.worker:
            self.worker.cancel()

    def action_pause_resume(self):
        if self.btn_pause.toolTip() == "Pause":
            self.btn_pause.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
            self.btn_pause.setToolTip("Resume")
            self.status_label.setText("⏸️ Paused")
            if hasattr(self, 'worker') and self.worker:
                self.worker.pause()
        else:
            self.btn_pause.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
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

class PlaylistThumbnail(ResponsiveImage):
    def __init__(self):
        super().__init__()
        self.video_count = 0

    def set_count(self, count):
        self.video_count = count
        self.update()

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