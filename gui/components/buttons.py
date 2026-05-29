from PyQt6.QtWidgets import QPushButton, QAbstractButton, QSizePolicy
from PyQt6.QtCore import Qt, QSize, QTimer, QRectF, QPropertyAnimation, pyqtProperty
from PyQt6.QtGui import QPainter, QBrush, QColor, QPen

class ToggleSwitch(QAbstractButton):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.setFixedSize(46, 22)
        self._thumb_position = 3.0
        self._animation = QPropertyAnimation(self, b"thumb_position", self)
        self._animation.setDuration(120)
        self.toggled.connect(self.start_animation)
    @pyqtProperty(float)

    def thumb_position(self):
        return self._thumb_position
    @thumb_position.setter

    def thumb_position(self, pos):
        self._thumb_position = pos
        self.update()

    def start_animation(self, checked):
        start = 3.0 if not checked else 25.0
        end = 25.0 if checked else 3.0
        self._animation.setStartValue(start)
        self._animation.setEndValue(end)
        self._animation.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        track_color = QColor("#3b82f6") if self.isChecked() else QColor("#475569")
        if not self.isEnabled():
            track_color = QColor(128, 128, 128, 60)
        painter.setBrush(QBrush(track_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, 46, 22, 11, 11)
        thumb_color = QColor(255, 255, 255)
        if not self.isEnabled():
            thumb_color = QColor(180, 180, 180)
        painter.setBrush(QBrush(thumb_color))
        painter.drawEllipse(int(self._thumb_position), 3, 16, 16)

class NotificationBellButton(QPushButton):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(32, 32)
        self.setFlat(True)
        self.setObjectName("BellBtn")
        self.setStyleSheet("""
            QPushButton#BellBtn { border-radius: 16px; border: none; background: transparent; } 
            QPushButton#BellBtn:hover { background-color: rgba(128, 128, 128, 0.2); }
        """)
        self.has_notifications = False
        self.pulse_radius = 3.5
        self.pulse_timer = QTimer(self)
        self.pulse_timer.timeout.connect(self.animate_pulse)
        self.pulse_timer.start(150)
        self.pulse_grow = True

    def set_has_notifications(self, has_notif):
        if self.has_notifications != has_notif:
            self.has_notifications = has_notif
            self.update()

    def animate_pulse(self):
        if not self.has_notifications:
            return
        if self.pulse_grow:
            self.pulse_radius += 0.4
            if self.pulse_radius >= 6.5:
                self.pulse_grow = False
        else:
            self.pulse_radius -= 0.4
            if self.pulse_radius <= 3.5:
                self.pulse_grow = True
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.has_notifications:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            pulse_color = QColor(239, 68, 68, 80)
            painter.setBrush(QBrush(pulse_color))
            painter.setPen(Qt.PenStyle.NoPen)
            center_x = self.width() - 6.5
            center_y = 5.5
            painter.drawEllipse(QRectF(center_x - self.pulse_radius, center_y - self.pulse_radius, self.pulse_radius * 2, self.pulse_radius * 2))
            dot_color = QColor("#ef4444")
            painter.setBrush(QBrush(dot_color))
            painter.drawEllipse(QRectF(center_x - 3.0, center_y - 3.0, 6.0, 6.0))

class DownloadProgressButton(QPushButton):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(32, 32)
        self.setFlat(True)
        self.setObjectName("DlProgressBtn")
        self.setStyleSheet("""
            QPushButton#DlProgressBtn { border-radius: 16px; border: none; background: transparent; } 
            QPushButton#DlProgressBtn:hover { background-color: rgba(128, 128, 128, 0.2); }
        """)
        self.percentage = 0.0
        self.is_active = False

    def set_progress(self, percentage, is_active=True):
        self.percentage = percentage
        self.is_active = is_active
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.is_active and self.percentage > 0:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            pen_track = QPen(QColor(128, 128, 128, 40), 2)
            painter.setPen(pen_track)
            painter.drawEllipse(2, 2, 28, 28)
            pen_arc = QPen(QColor("#3b82f6"), 2)
            pen_arc.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen_arc)
            span_angle = -int(self.percentage * 3.6 * 16)
            painter.drawArc(2, 2, 28, 28, 90 * 16, span_angle)
