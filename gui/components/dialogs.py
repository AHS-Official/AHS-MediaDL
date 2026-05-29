import os
import re
import json
from PyQt6.QtWidgets import (QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QScrollArea, QProgressBar, QDialog, 
                             QListWidget, QListWidgetItem, QLineEdit, QApplication,
                             QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, QSize, QTimer, QPropertyAnimation, QRectF
from PyQt6.QtGui import QPainter, QColor
from utils.helpers import get_colored_icon, get_current_theme_color
from utils.locales import tr

class NotificationsPopup(QFrame):

    def __init__(self, main_app, parent=None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
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
                card.setStyleSheet(f"QWidget#NotifCard {{  background-color: {card_color}; border-radius: 8px; padding: 8px; }} ")
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
        cards = self.main_app.page_downloads.get_download_cards()
        total_count = len(cards)
        completed_count = 0
        active_count = 0
        total_speed_bytes = 0.0
        max_eta_seconds = 0
        for card in cards:
            if hasattr(card, 'p_bar'):
                val = card.p_bar.value()
                if val == 100:
                    completed_count += 1
                else:
                    active_count += 1
            if hasattr(card, 'status_label') and hasattr(card, 'worker') and card.worker:
                status_text = card.status_label._full_text
                speed_match = re.search(r'Speed:\s*([\d\.]+)\s*([KM]i?B|B)/s', status_text, re.IGNORECASE)
                if speed_match:
                    val = float(speed_match.group(1))
                    unit = speed_match.group(2).upper()
                    if 'M' in unit:
                        total_speed_bytes += val * 1024 * 1024
                    elif 'K' in unit:
                        total_speed_bytes += val * 1024
                    else:
                        total_speed_bytes += val
                eta_match = re.search(r'ETA:\s*([\d:]+)', status_text, re.IGNORECASE)
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
            speed_str = f"{total_speed_bytes:.1f} B/s"
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
        self.setFixedSize(320, 130)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        frame = QFrame(self)
        frame.setObjectName("ToastFrame")
        theme = "dark"
        if self.parent_win and hasattr(self.parent_win, 'settings_file'):
            try:
                import json
                with open(self.parent_win.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    theme = data.get("theme", "auto")
            except:
                pass
        if theme == "auto":
            from PyQt6.QtGui import QGuiApplication
            scheme = QGuiApplication.styleHints().colorScheme()
            theme = "dark" if scheme == Qt.ColorScheme.Dark else "light"
        if theme == "dark":
            frame.setStyleSheet("""
                QFrame#ToastFrame {
                    background-color: rgba(30, 31, 34, 0.95);
                    border: 1px solid rgba(255, 94, 58, 0.4);
                    border-radius: 12px;
                }
            """)
            sub_color = "#94a3b8"
        else:
            frame.setStyleSheet("""
                QFrame#ToastFrame {
                    background-color: rgba(255, 255, 255, 0.95);
                    border: 1px solid rgba(255, 94, 58, 0.4);
                    border-radius: 12px;
                }
            """)
            sub_color = "#475569"
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(12, 12, 12, 12)
        frame_layout.setSpacing(8)
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"font-size: 13px; font-weight: bold; color: #ff5e3a; background: transparent; border: none;")
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
        self.btn_yes.setStyleSheet("""
            QPushButton {
                background-color: #ff5e3a;
                color: white;
                font-weight: bold;
                border-radius: 6px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #ff7e5a;
            }
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

class PackagesDialog(QDialog):

    def __init__(self, parent_page=None):
        super().__init__(parent_page)
        self.parent_page = parent_page
        self.settings_file = parent_page.main_app.settings_file
        self.setObjectName("PackagesDialog")
        self.setWindowTitle(tr("packages_title", "Collected Links Box"))
        self.setFixedWidth(380)
        self.setMinimumHeight(400)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.initUI()
        self.load_links()

    def initUI(self):
        is_dark = get_current_theme_color() == "#f1f5f9"
        bg_color = "#0b0f19" if is_dark else "#f8fafc"
        bg_card = "#131926" if is_dark else "#ffffff"
        border_color = "#1e293b" if is_dark else "#e2e8f0"
        text_color = "#f1f5f9" if is_dark else "#0f172a"
        self.setStyleSheet(f"""
            QDialog {{ 
                background-color: {bg_color};
            }} 
            QLineEdit {{ 
                background-color: {bg_card};
                border: 1px solid {border_color};
                border-radius: 8px;
                padding: 8px 12px;
                color: {text_color};
            }} 
            QLineEdit:focus {{ 
                border: 1px solid #3b82f6;
            }} 
            QListWidget {{ 
                background-color: {bg_card};
                border: 1px solid {border_color};
                border-radius: 10px;
                color: {text_color};
                padding: 5px;
            }} 
            QListWidget::item {{ 
                padding: 10px;
                border-bottom: 1px solid {border_color}33;
                color: {text_color};
            }} 
            QListWidget::item:hover {{ 
                background-color: rgba(59, 130, 246, 0.15);
                border-radius: 6px;
            }} 
            QPushButton {{ 
                background-color: {bg_card};
                border: 1px solid {border_color};
                border-radius: 8px;
                padding: 8px 16px;
                color: {text_color};
                font-weight: bold;
                font-size: 12px;
            }} 
            QPushButton:hover {{ 
                background-color: rgba(59, 130, 246, 0.1);
                border: 1px solid #3b82f6;
            }} 
            QPushButton#btn_download_all {{ 
                background-color: #3b82f6;
                color: white;
                border: none;
            }} 
            QPushButton#btn_download_all:hover {{ 
                background-color: #60a5fa;
            }} 
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)
        title_lbl = QLabel(tr("packages_title"))
        title_lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #3b82f6; background: transparent; border: none;")
        layout.addWidget(title_lbl)
        add_layout = QHBoxLayout()
        self.input_url = QLineEdit()
        self.input_url.setPlaceholderText(tr("url_placeholder"))
        self.input_url.returnPressed.connect(self.add_link)
        self.btn_add = QPushButton()
        self.btn_add.setIcon(get_colored_icon("assets/icons/save.svg", get_current_theme_color()))
        self.btn_add.setIconSize(QSize(16, 16))
        self.btn_add.setFixedWidth(40)
        self.btn_add.clicked.connect(self.add_link)
        add_layout.addWidget(self.input_url)
        add_layout.addWidget(self.btn_add)
        layout.addLayout(add_layout)
        self.list_widget = QListWidget()
        self.list_widget.setToolTip(tr("packages_tooltip"))
        self.list_widget.itemDoubleClicked.connect(self.remove_item)
        layout.addWidget(self.list_widget)
        btn_layout = QHBoxLayout()
        self.btn_clear = QPushButton(tr("btn_clear_all"))
        self.btn_clear.setIcon(get_colored_icon("assets/icons/broom.svg", get_current_theme_color()))
        self.btn_clear.setIconSize(QSize(14, 14))
        self.btn_clear.clicked.connect(self.clear_all)
        self.btn_dl_all = QPushButton(tr("btn_download_all"))
        self.btn_dl_all.setObjectName("btn_download_all")
        self.btn_dl_all.setIcon(get_colored_icon("assets/icons/download.svg", "#ffffff"))
        self.btn_dl_all.setIconSize(QSize(14, 14))
        self.btn_dl_all.clicked.connect(self.download_all)
        btn_layout.addWidget(self.btn_clear)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_dl_all)
        layout.addLayout(btn_layout)

    def load_links(self):
        self.list_widget.clear()
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    links = data.get("collected_links", [])
                    if not links:
                        item = QListWidgetItem(tr("packages_empty"))
                        item.setFlags(Qt.ItemFlag.NoItemFlags)
                        self.list_widget.addItem(item)
                        self.btn_dl_all.setEnabled(False)
                        self.btn_clear.setEnabled(False)
                    else:
                        for url in links:
                            self.list_widget.addItem(url)
                        self.btn_dl_all.setEnabled(True)
                        self.btn_clear.setEnabled(True)
            except Exception:
                pass

    def add_link(self):
        url = self.input_url.text().strip()
        if not url:
            return
        data = {}
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception:
                pass
        links = data.get("collected_links", [])
        if url not in links:
            links.append(url)
            data["collected_links"] = links
            try:
                with open(self.settings_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
            except Exception:
                pass
        self.input_url.clear()
        self.load_links()

    def remove_item(self, item):
        url = item.text()
        if url == tr("packages_empty"):
            return
        data = {}
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception:
                pass
        links = data.get("collected_links", [])
        if url in links:
            links.remove(url)
            data["collected_links"] = links
            try:
                with open(self.settings_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
            except Exception:
                pass
        self.load_links()

    def clear_all(self):
        data = {}
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception:
                pass
        data["collected_links"] = []
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception:
            pass
        self.load_links()

    def download_all(self):
        settings_file = self.settings_file
        collected_urls = []
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    collected_urls = data.get("collected_links", [])
            except Exception:
                pass
        if collected_urls:
            self.clear_all()
            self.close()
            self.parent_page.inspect_custom_links(collected_urls)
        else:
            self.close()
