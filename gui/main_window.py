import os
import json
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QTabWidget, QStackedWidget, QApplication, 
                             QSystemTrayIcon, QMenu, QMessageBox)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QPixmap, QColor, QPainter

from utils import strings
from utils.settings import app_config
from gui.theme import styled
from gui.settings_page import SettingsWidget

# استدعاء التابات المستقلة
from gui.tabs.tab_home import HomeTab
from gui.tabs.tab_queue import DownloadsTab
from gui.tabs.tab_history import HistoryTab

class DownloaderApp(QWidget):
    def __init__(self, startup_url=None):
        super().__init__()
        win_w = app_config.get("window_width", 700)
        win_h = app_config.get("window_height", 650)
        
        self.setWindowTitle(strings.APP_TITLE)
        self.setMinimumSize(600, 500)
        self.resize(win_w, win_h)

        # --- إعداد الهيكل الرئيسي والطبقات ---
        self.window_layout = QVBoxLayout(self)
        self.window_layout.setContentsMargins(0, 0, 0, 0)
        
        self.central_stacked = QStackedWidget()
        self.window_layout.addWidget(self.central_stacked)

        self.main_page = QWidget()
        self.settings_page = QWidget()
        
        self.central_stacked.addWidget(self.main_page)
        self.central_stacked.addWidget(self.settings_page)

        # --- الصفحة الرئيسية (تحتوي على التابات والشريط العلوي) ---
        self.main_layout = QVBoxLayout(self.main_page)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        
        # الشريط العلوي (زر الإعدادات)
        top_bar = QHBoxLayout()
        top_bar.addStretch() 
        self.settings_btn = styled.ghost_button(strings.BTN_SETTINGS)
        self.settings_btn.clicked.connect(self.go_to_settings)
        top_bar.addWidget(self.settings_btn)
        self.main_layout.addLayout(top_bar)
        
        # التابات الثلاثة
        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)

        # دمج التابات المنفصلة
        self.tab_home = HomeTab(self)
        self.tab_queue = DownloadsTab(self)
        self.tab_history = HistoryTab(self)

        self.tabs.addTab(self.tab_home, strings.APP_TAB_ADD)
        self.tabs.addTab(self.tab_queue, strings.APP_TAB_QUEUE)
        self.tabs.addTab(self.tab_history, strings.APP_TAB_HISTORY)
        
        self.tabs.currentChanged.connect(self.on_tab_changed)

        # --- إعداد النظام في الخلفية (System Tray) ---
        self.setup_system_tray()

        # --- معالجة رابط البدء لو موجود (Single Instance) ---
        if startup_url:
            self.tab_home.url_input.setText(startup_url)
            QTimer.singleShot(500, self.tab_home.fetch_video_info)

        # --- التحقق من وجود FFmpeg عند التشغيل ---
        QTimer.singleShot(1000, self.check_ffmpeg_availability)

    def check_ffmpeg_availability(self):
        from utils.helpers import is_ffmpeg_available
        if not is_ffmpeg_available():
            msg = (
                "⚠️ تحذير: أداة FFmpeg غير مثبتة أو غير موجودة في مسار النظام.\n"
                "بعض صيغ التحميل (مثل الدمج والجودة العالية جداً) قد لا تعمل بشكل صحيح بدونها."
                if strings.is_ar else
                "⚠️ Warning: FFmpeg is not installed or not found in system PATH.\n"
                "Some download formats (like merging and high resolutions) may not work properly without it."
            )
            QMessageBox.warning(self, strings.APP_TITLE, msg)

    def setup_system_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        
        # رسم أيقونة افتراضية أو تحميل الأيقونة الأصلية
        from utils.helpers import resource_path
        icon_path = resource_path(os.path.join('assets', 'icon.ico'))
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        else:
            pixmap = QPixmap(64, 64)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.setBrush(QColor("#4d78cc"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(4, 4, 56, 56)
            painter.end()
            self.tray_icon.setIcon(QIcon(pixmap))
            
        self.tray_icon.setToolTip(strings.APP_TITLE)
        
        tray_menu = QMenu()
        show_action = tray_menu.addAction("🖥️ إظهار التطبيق" if strings.is_ar else "🖥️ Show App")
        show_action.triggered.connect(self.show_normal_and_activate)

        quick_add_action = tray_menu.addAction("⚡ تحميل سريع من الحافظة" if strings.is_ar else "⚡ Quick Add from Clipboard")
        quick_add_action.triggered.connect(self.quick_download_from_clipboard)

        batch_action = tray_menu.addAction("📦 إضافة مجموعة روابط" if strings.is_ar else "📦 Batch Download")
        batch_action.triggered.connect(self.tab_home.open_batch_dialog)
        
        tray_menu.addSeparator()

        quit_action = tray_menu.addAction("❌ إغلاق التطبيق نهائياً" if strings.is_ar else "❌ Quit App")
        quit_action.triggered.connect(QApplication.instance().quit)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    # --- دوال التحكم في الواجهة ---
    def on_tab_changed(self, index):
        if self.tabs.tabText(index) == strings.APP_TAB_HISTORY:
            self.tab_history.load_history()

    def go_to_settings(self):
        if not self.settings_page.layout():
            self.setup_settings_ui()
        self.central_stacked.setCurrentIndex(1)

    def go_to_main(self):
        self.central_stacked.setCurrentIndex(0)

    def setup_settings_ui(self):
        layout = QVBoxLayout(self.settings_page)
        layout.setContentsMargins(0, 0, 0, 0)

        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(15, 10, 15, 0)
        
        back_text = "⬅️ رجوع للرئيسية" if strings.is_ar else "⬅️ Back to Home"
        back_btn = styled.ghost_button(back_text)
        back_btn.setFixedSize(160, 35)
        back_btn.clicked.connect(self.go_to_main)
        
        top_bar.addWidget(back_btn)
        top_bar.addStretch()
        
        layout.addLayout(top_bar)

        # ربط صفحة الإعدادات المستقلة
        self.settings_content = SettingsWidget(go_back_callback=self.go_to_main)
        layout.addWidget(self.settings_content, stretch=1)

    def save_to_history(self, history_entry):
        from utils.helpers import get_app_dir
        history_file = os.path.join(get_app_dir(), "history.json")
        history_data = []
        if os.path.exists(history_file):
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    history_data = json.load(f)
            except: 
                history_data = []
        
        history_data.insert(0, history_entry)
        
        try:
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(history_data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving history safely: {e}")
            
        self.tab_history.load_history()

    # --- دوال التشغيل في الخلفية والاختصارات ---
    def show_normal_and_activate(self):
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def quick_download_from_clipboard(self):
        clipboard = QApplication.clipboard()
        text = clipboard.text().strip()
        
        if text.startswith("http"):
            self.show_normal_and_activate()
            self.tabs.setCurrentIndex(0)
            self.tab_home.url_input.setText(text)
            self.tab_home.fetch_video_info()
        else:
            QMessageBox.warning(self, "تنبيه" if strings.is_ar else "Warning", 
                                "لا يوجد رابط صالح في الحافظة!" if strings.is_ar else "No valid link in clipboard!")

    def closeEvent(self, event):
        if app_config.get("close_to_tray", True) and QSystemTrayIcon.isSystemTrayAvailable():
            event.ignore()
            self.hide()
            if app_config.get("notifications", True):
                self.tray_icon.showMessage(
                    strings.APP_TITLE,
                    "التطبيق يعمل في الخلفية (الشريط العلوي)" if strings.is_ar else "App is running in the background",
                    QSystemTrayIcon.MessageIcon.Information,
                    2000
                )
        else:
            event.accept()
            QApplication.instance().quit()

