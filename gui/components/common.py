import os
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPainter
from utils.helpers import get_colored_icon, get_current_theme_color

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
