import os
import re
from datetime import datetime
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFrame, QPushButton
from PyQt6.QtCore import Qt, QSize, QTimer, QRect
from PyQt6.QtGui import QPainter, QColor, QPen, QTextLayout, QTextOption
from utils.helpers import get_colored_icon, get_current_theme_color, resource_path

def get_relative_time(upload_date_str):
    """يُحوِّل صيغة تاريخ الـ yt-dlp (YYYYMMDD) إلى صيغة نسبية مثل 'قبل 9 أيام'."""
    if not upload_date_str or len(upload_date_str) != 8:
        return ""
    try:
        dt = datetime.strptime(upload_date_str, "%Y%m%d")
        delta = datetime.now() - dt
        days = delta.days
        from utils.locales import lang
        if lang == "ar":
            if days <= 0: return "اليوم"
            elif days == 1: return "قبل يوم"
            elif days == 2: return "قبل يومين"
            elif days < 11: return f"قبل {days} أيام"
            elif days < 14: return "قبل أسبوع"
            elif days < 30: return f"قبل {days // 7} أسابيع"
            elif days < 60: return "قبل شهر"
            elif days < 365:
                months = days // 30
                if months == 2: return "قبل شهرين"
                elif months < 11: return f"قبل {months} أشهر"
                else: return f"قبل {months} شهراً"
            else:
                years = days // 365
                if years == 1: return "قبل سنة"
                elif years == 2: return "قبل سنتين"
                else: return f"قبل {years} سنوات"
        else:
            if days <= 0: return "today"
            elif days == 1: return "yesterday"
            elif days < 7: return f"{days} days ago"
            elif days < 14: return "1 week ago"
            elif days < 30: return f"{days // 7} weeks ago"
            elif days < 60: return "1 month ago"
            elif days < 365: return f"{days // 30} months ago"
            else:
                years = days // 365
                if years == 1: return "1 year ago"
                else: return f"{years} years ago"
    except Exception:
        return ""

def format_views(view_count):
    """يُنسِّق عدد المشاهدات ليطابق شكل مشاهدات اليوتيوب المألوف."""
    if not view_count:
        return ""
    try:
        vc = int(view_count)
        from utils.locales import lang
        if lang == "ar":
            if vc >= 1000000000: return f"{vc / 1000000000:.1f} مليار مشاهدة"
            elif vc >= 1000000: return f"{vc / 1000000:.1f} مليون مشاهدة"
            elif vc >= 1000: return f"{vc / 1000:.1f} ألف مشاهدة"
            else: return f"{vc} مشاهدة"
        else:
            if vc >= 1000000000: return f"{vc / 1000000000:.1f}B views"
            elif vc >= 1000000: return f"{vc / 1000000:.1f}M views"
            elif vc >= 1000: return f"{vc / 1000:.1f}K views"
            else: return f"{vc} views"
    except Exception:
        return str(view_count)

class FormatPreferencesMixin:
    """Mixin للمكونات التي تختار الجودة وتدعم ميزة تذكر الجودة"""

    def auto_select_saved_format(self):
        if not hasattr(self, 'remember_choice_cb') or not hasattr(self, 'format_combo') or not hasattr(self, 'main_app'):
            return
        if not self.remember_choice_cb.isChecked():
            return
            
        settings = self.main_app.settings_manager
        saved_choice = settings.get("saved_format_choice", "")
        if not saved_choice:
            return

        self.format_combo.blockSignals(True)
        try:
            if saved_choice == "audio":
                for i in range(self.format_combo.count()):
                    code = self.format_combo.itemData(i)
                    if code and str(code).startswith("audio:"):
                        self.format_combo.setCurrentIndex(i)
                        break
            else:
                for i in range(self.format_combo.count()):
                    code = self.format_combo.itemData(i)
                    if code and not str(code).startswith("audio:") and f"height<={saved_choice}" in str(code):
                        self.format_combo.setCurrentIndex(i)
                        break
        finally:
            self.format_combo.blockSignals(False)

    def save_format_preference(self):
        if not hasattr(self, 'remember_choice_cb') or not hasattr(self, 'format_combo') or not hasattr(self, 'main_app'):
            return
        if not self.remember_choice_cb.isChecked():
            return
            
        current_code = self.format_combo.currentData()
        if not current_code:
            return
            
        pref = ""
        current_code_str = str(current_code)
        if current_code_str.startswith("audio:"):
            pref = "audio"
        else:
            match = re.search(r'height<=(144|240|360|480|720|1080|1440|2160)', current_code_str)
            if match:
                pref = match.group(1)
                
        if pref:
            settings = self.main_app.settings_manager
            settings.set("saved_format_choice", pref)
            settings.set("remember_format_choice", True)
            settings.save()

    def on_remember_choice_toggled(self, checked):
        if not hasattr(self, 'format_combo') or not hasattr(self, 'main_app'):
            return
            
        settings = self.main_app.settings_manager
        settings.set("remember_format_choice", checked)
        
        if checked:
            current_code = self.format_combo.currentData()
            if current_code:
                pref = ""
                current_code_str = str(current_code)
                if current_code_str.startswith("audio:"):
                    pref = "audio"
                else:
                    match = re.search(r'height<=(144|240|360|480|720|1080|1440|2160)', current_code_str)
                    if match:
                        pref = match.group(1)
                if pref:
                    settings.set("saved_format_choice", pref)
                    
        settings.save()

class LoadingSpinner(QWidget):
    def __init__(self, size=24, color="#3b82f6", parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.color = color
        self._angle = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_rotation)
        
    def _update_rotation(self):
        self._angle = (self._angle + 30) % 360
        self.update()

    def start(self):
        self.show()
        self.timer.start(80)

    def stop(self):
        self.timer.stop()
        self.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.translate(self.width() / 2, self.height() / 2)
        painter.rotate(self._angle)
        
        pen = QPen()
        pen.setWidth(3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        
        for i in range(12):
            color = QColor(self.color)
            color.setAlphaF((i + 1) / 12.0)
            pen.setColor(color)
            painter.setPen(pen)
            painter.drawLine(0, int(self.width() / 4), 0, int(self.width() / 2) - 2)
            painter.rotate(30)

class ResponsiveImage(QLabel):

    def __init__(self, min_height=120, spinner_size=28):
        super().__init__()
        self._pixmap = None
        self._duration_text = ""
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(self.sizePolicy().Policy.Expanding, self.sizePolicy().Policy.Expanding)
        self.setMinimumHeight(min_height)
        self.setStyleSheet("background-color: #1a2035; border-radius: 8px; border: 1px solid #1e293b;")
        
        self.spinner = LoadingSpinner(size=spinner_size, color="#3b82f6", parent=self)
        self.spinner.hide()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.spinner, 0, Qt.AlignmentFlag.AlignCenter)

    def set_duration_text(self, text):
        self._duration_text = text
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if hasattr(self, '_duration_text') and self._duration_text:
            from PyQt6.QtGui import QPainter, QColor, QFont
            from PyQt6.QtCore import QRect
            
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            if self._pixmap and not self.size().isEmpty():
                scaled_size = self._pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio).size()
                x = (self.width() - scaled_size.width()) // 2
                y = (self.height() - scaled_size.height()) // 2
                w = scaled_size.width()
                h = scaled_size.height()
            else:
                x = 0
                y = 0
                w = self.width()
                h = self.height()
                
            font = QFont("Inter", 8)
            font.setBold(True)
            painter.setFont(font)
            
            metrics = painter.fontMetrics()
            tw = metrics.horizontalAdvance(self._duration_text)
            th = metrics.height()
            
            pad_x = 5
            pad_y = 1
            bw = tw + 2 * pad_x
            bh = th + 2 * pad_y
            
            bx = x + w - bw - 4
            by = y + h - bh - 4
            
            # Semi-translucent black rounded rect for the badge
            painter.setBrush(QColor(0, 0, 0, 200))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRect(bx, by, bw, bh), 3, 3)
            
            # Text
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(bx + pad_x, by + pad_y + metrics.ascent(), self._duration_text)

    def sizeHint(self):
        return QSize(120, 120)

    def show_loading(self):
        self.clear()
        self._pixmap = None
        self._duration_text = ""
        self.spinner.show()
        self.spinner.start()

    def hide_loading(self):
        self.spinner.stop()
        self.spinner.hide()

    def setPixmap(self, pixmap):
        self.hide_loading()
        self._pixmap = pixmap
        self.update_image()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._pixmap:
            self.update_image()

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

class PulsingGlowRing(QWidget):
    """حلقة glow متحركة بهدوء حول الأيقونة بلون الأكسنت."""
    def __init__(self, size=96, accent="#3b82f6", parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._accent = accent
        self._alpha = 40
        self._growing = True
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._pulse)
        self._timer.start(50)

    def set_accent(self, accent):
        self._accent = accent
        self.update()

    def _pulse(self):
        step = 2
        if self._growing:
            self._alpha += step
            if self._alpha >= 90:
                self._growing = False
        else:
            self._alpha -= step
            if self._alpha <= 20:
                self._growing = True
        self.update()

    def paintEvent(self, event):
        from PyQt6.QtGui import QPainter, QColor, QPen
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = QColor(self._accent)
        c.setAlpha(self._alpha)
        pen = QPen(c, 2)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        margin = 6
        painter.drawEllipse(margin, margin, self.width() - 2 * margin, self.height() - 2 * margin)
        # Inner fill
        c2 = QColor(self._accent)
        c2.setAlpha(self._alpha // 4)
        painter.setBrush(c2)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(margin + 4, margin + 4, self.width() - 2 * (margin + 4), self.height() - 2 * (margin + 4))

    def showEvent(self, event):
        if not self._timer.isActive():
            self._timer.start(50)
        super().showEvent(event)

    def hideEvent(self, event):
        if self._timer.isActive():
            self._timer.stop()
        super().hideEvent(event)

class EmptyStateWidget(QWidget):

    def __init__(self, icon_path, title, subtitle="", parent=None, image_path=None):
        super().__init__(parent)
        self.icon_path = icon_path
        self.original_title = title
        self.original_subtitle = subtitle
        self.image_path = None
        self._action_btn = None
        self._hint_lbl = None
        self.setSizePolicy(self.sizePolicy().Policy.Expanding, self.sizePolicy().Policy.Expanding)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.container = QFrame()
        self.container.setObjectName("EmptyStateContainer")
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(40, 40, 40, 40)
        container_layout.setSpacing(14)

        from utils.theme import get_accent_hex
        acc = get_accent_hex()

        # ── Loading Spinner (hidden by default) ──────────────────────────────
        self.spinner = LoadingSpinner(size=36, color=acc, parent=self)
        self.spinner.hide()
        container_layout.addWidget(self.spinner, 0, Qt.AlignmentFlag.AlignCenter)

        # ── Icon stack: glow ring + icon label ───────────────────────────────
        self.icon_stack = QWidget()
        self.icon_stack.setFixedSize(96, 96)
        self.icon_stack.setStyleSheet("background: transparent;")

        self.glow_ring = PulsingGlowRing(size=96, accent=acc, parent=self.icon_stack)
        self.glow_ring.move(0, 0)

        self.icon_label = QLabel(self.icon_stack)
        self.icon_label.setObjectName("EmptyStateIcon")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setFixedSize(96, 96)
        self.icon_label.setStyleSheet("background: transparent;")
        pixmap = get_colored_icon(icon_path, get_current_theme_color()).pixmap(QSize(52, 52))
        self.icon_label.setPixmap(pixmap)

        container_layout.addWidget(self.icon_stack, 0, Qt.AlignmentFlag.AlignCenter)
        # ── Title ────────────────────────────────────────────────────────────
        self.title_label = QLabel(title)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setWordWrap(True)
        title_font = self.title_label.font()
        title_font.setBold(True)
        title_font.setPointSize(title_font.pointSize() + 4)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet(f"color: {acc}; background: transparent; font-weight: 700; letter-spacing: 0.3px;")
        container_layout.addWidget(self.title_label)

        # ── Subtitle ─────────────────────────────────────────────────────────
        if subtitle:
            self.subtitle_label = QLabel(subtitle)
            self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.subtitle_label.setWordWrap(True)
            self.subtitle_label.setStyleSheet("color: #64748b; background: transparent; font-size: 12px; line-height: 1.5;")
            container_layout.addWidget(self.subtitle_label)

        # ── Action button placeholder (added via set_action) ─────────────────
        self._btn_area = QVBoxLayout()
        self._btn_area.setSpacing(6)
        container_layout.addSpacing(4)
        container_layout.addLayout(self._btn_area)

        main_layout.addStretch(1)
        main_layout.addWidget(self.container, 0, Qt.AlignmentFlag.AlignCenter)
        main_layout.addStretch(1)

    def set_action(self, btn_text, callback, hint_text=""):
        """يضيف زر أكشن تحت الـ empty state مع hint text اختياري."""
        from utils.theme import get_accent_hex
        acc = get_accent_hex()
        if self._action_btn:
            self._action_btn.deleteLater()
        if self._hint_lbl:
            self._hint_lbl.deleteLater()

        self._action_btn = QPushButton(btn_text)
        self._action_btn.setFixedHeight(40)
        self._action_btn.setMinimumWidth(180)
        self._action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._action_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #1d4ed8);
                color: #ffffff;
                border: none;
                border-radius: 10px;
                font-weight: 700;
                font-size: 13px;
                padding: 0 22px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #60a5fa, stop:1 #3b82f6);
            }}
            QPushButton:pressed {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1d4ed8, stop:1 #1e3a8a);
            }}
        """)
        self._action_btn.clicked.connect(callback)
        self._btn_area.addWidget(self._action_btn, 0, Qt.AlignmentFlag.AlignCenter)

        if hint_text:
            self._hint_lbl = QLabel(hint_text)
            self._hint_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._hint_lbl.setStyleSheet("color: #475569; background: transparent; font-size: 11px;")
            self._btn_area.addWidget(self._hint_lbl, 0, Qt.AlignmentFlag.AlignCenter)

    def show_loading(self, loading_title=""):
        if loading_title:
            self.title_label.setText(loading_title)
        if hasattr(self, 'subtitle_label'):
            self.subtitle_label.hide()
        if hasattr(self, 'icon_stack'):
            self.icon_stack.hide()
        self.icon_label.hide()
        self.glow_ring.hide()
        self.spinner.show()
        self.spinner.start()

    def hide_loading(self):
        self.spinner.stop()
        self.spinner.hide()
        if hasattr(self, 'icon_stack'):
            self.icon_stack.show()
        self.icon_label.show()
        self.glow_ring.show()
        pixmap = get_colored_icon(self.icon_path, get_current_theme_color()).pixmap(QSize(52, 52))
        self.icon_label.setPixmap(pixmap)
        if hasattr(self, 'original_title'):
            self.title_label.setText(self.original_title)
        if hasattr(self, 'original_subtitle') and hasattr(self, 'subtitle_label'):
            self.subtitle_label.setText(self.original_subtitle)
            self.subtitle_label.show()

    def update_icon_color(self, icon_path, icon_color):
        self.icon_path = icon_path
        if hasattr(self, 'icon_label') and self.icon_label is not None:
            pixmap = get_colored_icon(icon_path, icon_color).pixmap(QSize(52, 52))
            self.icon_label.setPixmap(pixmap)

    def update_accent_color(self):
        from utils.theme import get_accent_hex
        acc = get_accent_hex()
        self.spinner.color = acc
        self.title_label.setStyleSheet(f"color: {acc}; background: transparent; font-weight: 700; letter-spacing: 0.3px;")
        self.glow_ring.set_accent(acc)


class MultiLineElidedLabel(QLabel):
    """Label يعرض نصاً يلتف حتى سطرين كحد أقصى، ويضع نقاط الحذف (...) في النهاية."""
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._full_text = text
        self.setToolTip(text)
        self.setSizePolicy(self.sizePolicy().Policy.Expanding, self.sizePolicy().Policy.Preferred)

    def setText(self, text):
        self._full_text = text
        self.setToolTip(text)
        super().setText(text)
        self.update()

    def sizeHint(self):
        metrics = self.fontMetrics()
        if not self._full_text:
            return QSize(self.width(), 0)
        
        text_layout = QTextLayout(self._full_text, self.font())
        text_layout.beginLayout()
        count = 0
        width = self.width() if self.width() > 0 else 200
        while True:
            line = text_layout.createLine()
            if not line.isValid():
                break
            line.setLineWidth(width)
            count += 1
            if count >= 2:
                break
        text_layout.endLayout()
        
        return QSize(self.width(), metrics.lineSpacing() * max(1, count))

    def minimumSizeHint(self):
        metrics = self.fontMetrics()
        return QSize(50, metrics.lineSpacing())

    def paintEvent(self, event):
        painter = QPainter(self)
        metrics = self.fontMetrics()
        
        text_layout = QTextLayout(self._full_text, self.font())
        # Let alignment match parent or default to AlignLeading
        text_layout.setTextOption(QTextOption(self.alignment()))
        text_layout.beginLayout()
        
        lines = []
        width = self.width()
        while True:
            line = text_layout.createLine()
            if not line.isValid():
                break
            line.setLineWidth(width)
            lines.append(line)
        
        text_layout.endLayout()
        
        y = 0
        line_height = metrics.lineSpacing()
        for i in range(min(len(lines), 2)):
            line = lines[i]
            start = line.textStart()
            length = line.textLength()
            
            rect = QRect(0, y, width, line_height)
            if i == 1 and len(lines) > 2:
                remaining_text = self._full_text[start:]
                elided = metrics.elidedText(remaining_text, Qt.TextElideMode.ElideRight, width)
                painter.drawText(rect, self.alignment(), elided)
            else:
                line_text = self._full_text[start:start+length]
                painter.drawText(rect, self.alignment(), line_text)
                
            y += line_height

