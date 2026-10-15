"""
popups.py
─────────
يجمع كافة النوافذ المنبثقة والتنبيهات العائمة:
  1. NotificationsPopup — نافذة الإشعارات المنبثقة
  2. DownloadsPopup     — نافذة ملخص التنزيلات المنبثقة
  3. InteractiveToast   — إشعار تفاعلي عائم لروابط الحافظة
  4. NetworkStatsDialog — نافذة إحصائيات ورسم بياني للشبكة
"""
import re
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QProgressBar, QWidget, QPushButton,
    QGraphicsDropShadowEffect, QApplication
)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation
from PyQt6.QtGui import QPainter, QColor, QPen, QLinearGradient, QPainterPath

from utils.locales import tr
from utils.theme import get_accent_hex, hex_to_rgb
from managers.network_manager import NetworkTracker
from managers.settings_manager import SettingsManager


class NotificationsPopup(QFrame):

    def __init__(self, main_app, parent=None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.main_app = main_app
        self.setObjectName("NotifPopup")
        self.setFixedWidth(300)
        self.setMinimumHeight(150)
        self.setMaximumHeight(350)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setXOffset(0)
        shadow.setYOffset(5)
        shadow.setColor(QColor(0, 0, 0, 120))
        self.setGraphicsEffect(shadow)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        header_lbl = QLabel(tr("notifications_title", "Recent Notifications"))
        font = header_lbl.font()
        font.setBold(True)
        font.setPointSize(font.pointSize() + 1)
        header_lbl.setFont(font)
        header_lbl.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(header_lbl)
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet("background-color: rgba(128, 128, 128, 0.15);")
        layout.addWidget(div)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.list_widget = QWidget()
        self.list_widget.setStyleSheet("background: transparent;")
        self.list_layout = QVBoxLayout(self.list_widget)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(8)
        self.list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidget(self.list_widget)
        layout.addWidget(self.scroll)
        self.load_notifications()

    def load_notifications(self):
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        notifs = getattr(self.main_app, 'notifications_list', [])
        if not notifs:
            empty_lbl = QLabel(tr("no_new_notifications", "No notifications yet"))
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_lbl.setStyleSheet("color: #64748b; margin-top: 20px; background: transparent; border: none;")
            self.list_layout.addWidget(empty_lbl)
        else:
            for item in notifs:
                card = QWidget()
                card.setObjectName("NotifCard")
                card_color = "rgba(128, 128, 128, 0.15)" if not item.get("read", False) else "transparent"
                card.setStyleSheet(f"QWidget#NotifCard {{ background-color: {card_color}; border-radius: 8px; padding: 8px; }}")
                card_layout = QVBoxLayout(card)
                card_layout.setContentsMargins(8, 8, 8, 8)
                card_layout.setSpacing(4)
                top_layout = QHBoxLayout()
                t_lbl = QLabel(item.get("title", ""))
                t_lbl.setObjectName("NotifTitle")
                font = t_lbl.font()
                font.setBold(True)
                t_lbl.setFont(font)
                t_lbl.setStyleSheet("background: transparent; border: none;")
                time_lbl = QLabel(item.get("time", ""))
                time_lbl.setStyleSheet("color: #64748b; font-size: 10px; background: transparent; border: none;")
                time_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                top_layout.addWidget(t_lbl)
                top_layout.addStretch()
                top_layout.addWidget(time_lbl)
                card_layout.addLayout(top_layout)
                m_lbl = QLabel(item.get("message", ""))
                m_lbl.setObjectName("NotifMessage")
                m_lbl.setWordWrap(True)
                m_lbl.setStyleSheet("font-size: 11px; background: transparent; border: none;")
                card_layout.addWidget(m_lbl)
                self.list_layout.addWidget(card)
                item["read"] = True


class DownloadsPopup(QFrame):

    def __init__(self, main_app, parent=None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.main_app = main_app
        self.setObjectName("DlPopup")
        self.setFixedWidth(280)
        self.setMinimumHeight(110)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setXOffset(0)
        shadow.setYOffset(5)
        shadow.setColor(QColor(0, 0, 0, 120))
        self.setGraphicsEffect(shadow)
        self.initUI()
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_info)
        self.update_timer.start(500)

    def hideEvent(self, event):
        if hasattr(self, 'update_timer') and self.update_timer.isActive():
            self.update_timer.stop()
        super().hideEvent(event)

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)
        self.empty_lbl = QLabel(tr("no_downloads", "لا توجد تحميلات"))
        self.empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_lbl.setStyleSheet("color: #64748b; font-weight: bold; font-size: 14px; background: transparent; border: none; padding: 15px 0px;")
        layout.addWidget(self.empty_lbl)
        self.empty_lbl.hide()
        top_layout = QHBoxLayout()
        self.ratio_lbl = QLabel("0 / 0")
        self.ratio_lbl.setStyleSheet("font-weight: bold; font-size: 13px; background: transparent; border: none;")
        self.percentage_lbl = QLabel("0%")
        self.percentage_lbl.setStyleSheet("font-weight: bold; font-size: 13px; background: transparent; border: none;")
        self.percentage_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        top_layout.addWidget(self.ratio_lbl)
        top_layout.addStretch()
        top_layout.addWidget(self.percentage_lbl)
        layout.addLayout(top_layout)
        self.p_bar = QProgressBar()
        self.p_bar.setMinimumHeight(10)
        self.p_bar.setMaximumHeight(10)
        self.p_bar.setTextVisible(False)
        self.p_bar.setStyleSheet("""
            QProgressBar {
                background-color: rgba(128, 128, 128, 0.15);
                border-radius: 5px;
                border: none;
            }
            QProgressBar::chunk {
                background-color: #3b82f6;
                border-radius: 5px;
            }
        """)
        layout.addWidget(self.p_bar)
        bottom_layout = QHBoxLayout()
        self.speed_lbl = QLabel(tr("total_speed", "Total Speed: 0 KB/s"))
        self.speed_lbl.setStyleSheet("font-size: 11px; color: gray; background: transparent; border: none;")
        self.eta_lbl = QLabel(tr("time_left", "Time Left: N/A"))
        self.eta_lbl.setStyleSheet("font-size: 11px; color: gray; background: transparent; border: none;")
        self.eta_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        bottom_layout.addWidget(self.speed_lbl)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.eta_lbl)
        layout.addLayout(bottom_layout)
        self.update_info()

    def update_info(self):
        from PyQt6 import sip
        cards = self.main_app.page_downloads.get_download_cards()
        total_count = len(cards)
        completed_count = 0
        active_count = 0
        total_speed_bytes = 0.0
        max_eta_seconds = 0
        for card in cards:
            if hasattr(card, 'p_bar'):
                val = card.p_bar.value()
                if val == 100 or (hasattr(card, 'btn_open') and card.btn_open.isVisible()):
                    completed_count += 1
                elif hasattr(card, 'btn_cancel') and card.btn_cancel.isVisible():
                    active_count += 1
            if hasattr(card, 'worker') and card.worker and not sip.isdeleted(card.worker):
                if card.worker.isRunning() and not getattr(card.worker, 'is_paused', False):
                    total_speed_bytes += float(getattr(card.worker, 'current_speed_bps', 0) or 0)
            if hasattr(card, 'right_status_label') and card.right_status_label.isVisible():
                right_text = card.right_status_label.text()
                eta_match = re.search(r'⌛\s*([\d:]+)', right_text)
                if eta_match:
                    parts = eta_match.group(1).split(':')
                    try:
                        seconds = 0
                        if len(parts) == 2:
                            seconds = int(parts[0]) * 60 + int(parts[1])
                        elif len(parts) == 3:
                            seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                        if seconds > max_eta_seconds:
                            max_eta_seconds = seconds
                    except ValueError:
                        pass
        if total_count == 0:
            self.empty_lbl.show()
            self.ratio_lbl.hide()
            self.percentage_lbl.hide()
            self.p_bar.hide()
            self.speed_lbl.hide()
            self.eta_lbl.hide()
            self.setMinimumHeight(60)
            self.setMaximumHeight(80)
            return
        else:
            self.empty_lbl.hide()
            self.ratio_lbl.show()
            self.percentage_lbl.show()
            self.p_bar.show()
            if active_count == 0:
                self.speed_lbl.hide()
                self.eta_lbl.hide()
                self.setMinimumHeight(75)
                self.setMaximumHeight(90)
            else:
                self.speed_lbl.show()
                self.eta_lbl.show()
                self.setMinimumHeight(110)
                self.setMaximumHeight(150)
        avg_progress = int((completed_count / total_count) * 100) if total_count > 0 else 0
        self.ratio_lbl.setText(f"📥 {completed_count} / {total_count}")
        self.percentage_lbl.setText(f"{avg_progress}%")
        self.p_bar.setValue(avg_progress)
        if total_speed_bytes >= 1024 * 1024:
            speed_str = f"{total_speed_bytes / (1024 * 1024):.1f} MB/s"
        elif total_speed_bytes >= 1024:
            speed_str = f"{total_speed_bytes / 1024:.1f} KB/s"
        else:
            speed_str = f"{total_speed_bytes:.0f} B/s"
        self.speed_lbl.setText(f"{tr('total_speed', 'Total Speed')}: {speed_str}")
        if max_eta_seconds > 0 and active_count > 0:
            h = max_eta_seconds // 3600
            m = (max_eta_seconds % 3600) // 60
            s = max_eta_seconds % 60
            if h > 0:
                eta_str = f"{h:02d}:{m:02d}:{s:02d}"
            else:
                eta_str = f"{m:02d}:{s:02d}"
        else:
            eta_str = "N/A"
        self.eta_lbl.setText(f"{tr('time_left', 'Time Left')}: {eta_str}")


class InteractiveToast(QWidget):

    def __init__(self, title, message, url, callback, parent_win=None):
        super().__init__()
        self.url = url
        self.callback = callback
        self.parent_win = parent_win
        self.initUI(title, message)

    def initUI(self, title, message):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setFixedSize(320, 130)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        frame = QFrame(self)
        frame.setObjectName("ToastFrame")

        theme = SettingsManager().get("theme", "auto")
        if theme == "auto":
            from utils.helpers import detect_system_theme
            theme = detect_system_theme()

        acc_hex = get_accent_hex()
        rgb = hex_to_rgb(acc_hex)

        if theme == "dark":
            frame.setStyleSheet(f"""
                QFrame#ToastFrame {{
                    background-color: rgba(30, 31, 34, 0.95);
                    border: 1px solid rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, 0.45);
                    border-radius: 12px;
                }}
            """)
            sub_color = "#94a3b8"
        else:
            frame.setStyleSheet(f"""
                QFrame#ToastFrame {{
                    background-color: rgba(255, 255, 255, 0.95);
                    border: 1px solid rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, 0.45);
                    border-radius: 12px;
                }}
            """)
            sub_color = "#475569"

        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(12, 12, 12, 12)
        frame_layout.setSpacing(8)
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {acc_hex}; background: transparent; border: none;")
        msg_lbl = QLabel(message)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet(f"font-size: 11px; color: {sub_color}; background: transparent; border: none;")
        frame_layout.addWidget(title_lbl)
        frame_layout.addWidget(msg_lbl)
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        self.btn_yes = QPushButton(tr("btn_yes", "Yes"))
        self.btn_yes.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_yes.setFixedSize(80, 26)
        self.btn_yes.setStyleSheet(f"""
            QPushButton {{
                background-color: {acc_hex};
                color: white;
                font-weight: bold;
                border-radius: 6px;
                font-size: 11px;
            }}
        """)
        self.btn_yes.clicked.connect(self.accept)
        self.btn_no = QPushButton(tr("btn_no", "No"))
        self.btn_no.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_no.setFixedSize(80, 26)
        if theme == "dark":
            self.btn_no.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #94a3b8;
                    border: 1px solid #475569;
                    border-radius: 6px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.05);
                    color: white;
                }
            """)
        else:
            self.btn_no.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #475569;
                    border: 1px solid #cbd5e1;
                    border-radius: 6px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: rgba(0, 0, 0, 0.05);
                    color: black;
                }
            """)
        self.btn_no.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_no)
        btn_layout.addWidget(self.btn_yes)
        frame_layout.addLayout(btn_layout)
        layout.addWidget(frame)
        self.position_toast()
        self.setWindowOpacity(0.0)
        self.anim = QPropertyAnimation(self, b"windowOpacity")
        self.anim.setDuration(300)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(0.98)
        self.anim.start()
        self.close_timer = QTimer(self)
        self.close_timer.setSingleShot(True)
        self.close_timer.timeout.connect(self.reject)
        self.close_timer.start(10000)

    def position_toast(self):
        screen = QApplication.primaryScreen()
        screen_geo = screen.availableGeometry()
        x = screen_geo.x() + screen_geo.width() - self.width() - 15
        y = screen_geo.y() + screen_geo.height() - self.height() - 15
        self.move(x, y)

    def accept(self):
        self.close_timer.stop()
        self.callback(self.url)
        self.fade_out()

    def reject(self):
        self.close_timer.stop()
        self.fade_out()

    def fade_out(self):
        self.anim_out = QPropertyAnimation(self, b"windowOpacity")
        self.anim_out.setDuration(250)
        self.anim_out.setStartValue(self.windowOpacity())
        self.anim_out.setEndValue(0.0)
        self.anim_out.finished.connect(self.close)
        self.anim_out.start()


class NetworkChartWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(80)
        self.history = [0] * 60
        self.max_val = 1
        
    def update_data(self, history):
        self.history = history
        self.max_val = max(max(history) if history else 1, 1024 * 10)
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w = self.width()
        h = self.height()
        
        painter.setPen(QPen(QColor(255, 255, 255, 20), 1, Qt.PenStyle.DashLine))
        painter.drawLine(0, h // 2, w, h // 2)
        
        if not self.history:
            return
            
        accent = QColor(get_accent_hex())
        
        path = QPainterPath()
        fill_path = QPainterPath()
        
        step_x = w / max(len(self.history) - 1, 1)
        
        first_y = h - (self.history[0] / self.max_val) * h
        path.moveTo(0, first_y)
        fill_path.moveTo(0, h)
        fill_path.lineTo(0, first_y)
        
        for i, val in enumerate(self.history):
            x = i * step_x
            y = h - (val / self.max_val) * h
            path.lineTo(x, y)
            fill_path.lineTo(x, y)
            
        fill_path.lineTo(w, h)
        fill_path.closeSubpath()
        
        gradient = QLinearGradient(0, 0, 0, h)
        accent_fill = QColor(accent)
        accent_fill.setAlpha(80)
        gradient.setColorAt(0.0, accent_fill)
        gradient.setColorAt(1.0, QColor(accent.red(), accent.green(), accent.blue(), 0))
        
        painter.setBrush(gradient)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(fill_path)
        
        pen = QPen(accent, 2)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)


class NetworkStatsDialog(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(300)
        
        self.tracker = NetworkTracker()
        self._setup_ui()
        
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.refresh_stats)
        
    def _setup_ui(self):
        accent_hex = get_accent_hex()
        self.setStyleSheet(f"""
            QLabel {{
                color: white;
                background: transparent;
                border: none;
            }}
            QLabel#Title {{
                font-size: 14px;
                font-weight: bold;
                color: {accent_hex};
            }}
            QLabel#SubTitle {{
                font-size: 11px;
                color: #94a3b8;
            }}
            QLabel#Value {{
                font-size: 13px;
                font-weight: bold;
            }}
        """)
        self.setObjectName("NetworkStatsDialog")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        header = QLabel(tr("network_stats_title", "Network Activity"))
        header.setObjectName("Title")
        layout.addWidget(header)
        
        self.chart = NetworkChartWidget()
        layout.addWidget(self.chart)
        
        speeds_layout = QHBoxLayout()
        self.lbl_rx_speed = QLabel("↓ 0 KB/s")
        self.lbl_tx_speed = QLabel("↑ 0 KB/s")
        self.lbl_rx_speed.setObjectName("Value")
        self.lbl_tx_speed.setObjectName("Value")
        self.lbl_tx_speed.setStyleSheet("color: #94a3b8;")
        speeds_layout.addWidget(self.lbl_rx_speed)
        speeds_layout.addStretch()
        speeds_layout.addWidget(self.lbl_tx_speed)
        layout.addLayout(speeds_layout)
        
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet("background-color: rgba(255, 255, 255, 0.1); border: none;")
        layout.addWidget(line)
        
        session_layout = QHBoxLayout()
        lbl_sess = QLabel(tr("network_session", "Session Data:"))
        lbl_sess.setObjectName("SubTitle")
        self.lbl_session_data = QLabel("0 MB")
        self.lbl_session_data.setObjectName("Value")
        session_layout.addWidget(lbl_sess)
        session_layout.addStretch()
        session_layout.addWidget(self.lbl_session_data)
        layout.addLayout(session_layout)
        
        alltime_layout = QHBoxLayout()
        lbl_at = QLabel(tr("network_all_time", "All-Time Data:"))
        lbl_at.setObjectName("SubTitle")
        self.lbl_alltime_data = QLabel("0 MB")
        self.lbl_alltime_data.setObjectName("Value")
        alltime_layout.addWidget(lbl_at)
        alltime_layout.addStretch()
        alltime_layout.addWidget(self.lbl_alltime_data)
        layout.addLayout(alltime_layout)

    def format_size(self, bytes_size):
        if bytes_size < 1024:
            return f"{bytes_size} B"
        elif bytes_size < 1024 * 1024:
            return f"{bytes_size / 1024:.1f} KB"
        elif bytes_size < 1024 * 1024 * 1024:
            return f"{bytes_size / (1024 * 1024):.1f} MB"
        else:
            return f"{bytes_size / (1024 * 1024 * 1024):.2f} GB"

    def refresh_stats(self):
        stats = self.tracker.get_stats()
        self.chart.update_data(stats['rx_history'])
        self.lbl_rx_speed.setText(f"↓ {self.format_size(stats['rx_speed'])}/s")
        self.lbl_tx_speed.setText(f"↑ {self.format_size(stats['tx_speed'])}/s")
        
        total_session = stats['session_rx'] + stats['session_tx']
        self.lbl_session_data.setText(self.format_size(total_session))
        
        total_all_time = stats['all_time_rx'] + stats['all_time_tx']
        self.lbl_alltime_data.setText(self.format_size(total_all_time))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(30, 41, 59, 250))
        painter.setPen(QPen(QColor(255, 255, 255, 40), 1))
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 12, 12)

    def showEvent(self, event):
        self.refresh_stats()
        self.update_timer.start(1000)
        super().showEvent(event)

    def hideEvent(self, event):
        self.update_timer.stop()
        super().hideEvent(event)