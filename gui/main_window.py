import os
import json
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QStackedWidget, QApplication, QLabel, QFrame,
                             QSystemTrayIcon, QMenu, QMessageBox)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QPixmap, QColor, QPainter

from utils import strings
from utils.settings import app_config, save_settings
from utils.helpers import get_app_icon, get_app_icon_path
from gui.theme import styled, Theme, refresh_theme
from gui.settings_page import SettingsWidget

from gui.tabs.tab_home import HomeTab
from gui.tabs.tab_queue import DownloadsTab

class DownloaderApp(QWidget):
    def __init__(self, startup_url=None):
        super().__init__()
        self.setWindowTitle(strings.APP_TITLE)
        self.setWindowIcon(get_app_icon())
        self.setMinimumSize(780, 560)
        self.resize(920, 680)

        # الهيكل الرئيسي: شريط جانبي + مساحة العرض
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 1. الشريط الجانبي (Sidebar)
        self.sidebar_widget = QWidget()
        self.sidebar_widget.setObjectName("Sidebar")
        self.sidebar_widget.setFixedWidth(230)
        sidebar_layout = QVBoxLayout(self.sidebar_widget)
        sidebar_layout.setContentsMargins(14, 18, 14, 18)
        sidebar_layout.setSpacing(8)

        # عنوان وشعار التطبيق في الشريط الجانبي مع الأيقونة الجديدة
        brand_container = QWidget()
        brand_container.setStyleSheet("background: transparent; border: none;")
        brand_layout = QHBoxLayout(brand_container)
        brand_layout.setContentsMargins(0, 0, 0, 0)
        brand_layout.setSpacing(10)

        icon_path = get_app_icon_path()
        if icon_path:
            brand_img = QLabel()
            pix = QPixmap(icon_path)
            if not pix.isNull():
                brand_img.setPixmap(pix.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                brand_img.setFixedSize(32, 32)
                brand_img.setStyleSheet("background: transparent; border: none;")
                brand_layout.addWidget(brand_img)

        self.brand_label = QLabel(strings.APP_TITLE)
        self.brand_label.setObjectName("SidebarBrand")
        self.brand_label.setStyleSheet("background: transparent; border: none; font-size: 14pt; font-weight: 800;")
        brand_layout.addWidget(self.brand_label, stretch=1)
        sidebar_layout.addWidget(brand_container)
        sidebar_layout.addSpacing(14)

        # أزرار التنقل
        self.nav_home_btn = QPushButton("🏠  " + (strings.APP_TAB_ADD if hasattr(strings, 'APP_TAB_ADD') else "الرئيسية"))
        self.nav_home_btn.setObjectName("SidebarNavBtn")
        self.nav_home_btn.setProperty("active", "true")
        self.nav_home_btn.clicked.connect(lambda: self.switch_tab(0))

        self.queue_base_title = "📥  " + (strings.APP_TAB_QUEUE if hasattr(strings, 'APP_TAB_QUEUE') else "التنزيلات")
        self.nav_queue_btn = QPushButton(self.queue_base_title)
        self.nav_queue_btn.setObjectName("SidebarNavBtn")
        self.nav_queue_btn.clicked.connect(lambda: self.switch_tab(1))

        settings_title = "⚙️  " + ("الإعدادات" if strings.is_ar else "Settings")
        self.nav_settings_btn = QPushButton(settings_title)
        self.nav_settings_btn.setObjectName("SidebarNavBtn")
        self.nav_settings_btn.clicked.connect(lambda: self.switch_tab(2))

        sidebar_layout.addWidget(self.nav_home_btn)
        sidebar_layout.addWidget(self.nav_queue_btn)
        sidebar_layout.addWidget(self.nav_settings_btn)

        sidebar_layout.addStretch()

        # زر تبديل الثيم السريع (Dark / Light) في أسفل الشريط الجانبي
        self.theme_toggle_btn = QPushButton()
        self.theme_toggle_btn.setObjectName("ThemeToggleBtn")
        self.update_theme_toggle_label()
        self.theme_toggle_btn.clicked.connect(self.toggle_quick_theme)
        sidebar_layout.addWidget(self.theme_toggle_btn)

        self.main_layout.addWidget(self.sidebar_widget)

        # 2. مكدس الصفحات الرئيسي (QStackedWidget)
        self.stacked_widget = QStackedWidget()
        
        self.tab_home = HomeTab(self)
        self.tab_queue = DownloadsTab(self)
        self.tab_settings = SettingsWidget(self)

        self.stacked_widget.addWidget(self.tab_home)
        self.stacked_widget.addWidget(self.tab_queue)
        self.stacked_widget.addWidget(self.tab_settings)

        self.main_layout.addWidget(self.stacked_widget, stretch=1)

        # توافق مع أي استدعاء قديم لـ self.tabs
        self.tabs = self.stacked_widget

        # --- إعداد النظام في الخلفية (System Tray) ---
        self.setup_system_tray()

        # --- معالجة رابط البدء لو موجود ---
        if startup_url:
            self.tab_home.url_input.setText(startup_url)
            QTimer.singleShot(500, self.tab_home.fetch_video_info)

        # --- التحقق من وجود FFmpeg عند التشغيل ---
        QTimer.singleShot(1000, self.check_ffmpeg_availability)

    def switch_tab(self, index: int):
        self.stacked_widget.setCurrentIndex(index)
        
        # تحديث مظهر الأزرار النشطة
        self.nav_home_btn.setProperty("active", "true" if index == 0 else "false")
        self.nav_queue_btn.setProperty("active", "true" if index == 1 else "false")
        self.nav_settings_btn.setProperty("active", "true" if index == 2 else "false")

        # إعادة تطبيق الأنماط لتحديث الخاصية
        for btn in [self.nav_home_btn, self.nav_queue_btn, self.nav_settings_btn]:
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def update_downloads_badge(self, active_count: int):
        if active_count > 0:
            self.nav_queue_btn.setText(f"{self.queue_base_title}  ({active_count})")
        else:
            self.nav_queue_btn.setText(self.queue_base_title)

    def update_theme_toggle_label(self):
        is_dark = Theme.instance().is_dark()
        if strings.is_ar:
            self.theme_toggle_btn.setText("☀️ الوضع النهاري" if is_dark else "🌙 الوضع الليلي")
        else:
            self.theme_toggle_btn.setText("☀️ Light Mode" if is_dark else "🌙 Dark Mode")

    def toggle_quick_theme(self):
        Theme.instance().toggle()
        new_mode = Theme.instance().mode
        app_config["theme"] = new_mode
        save_settings(app_config)
        refresh_theme(QApplication.instance())
        self.update_theme_toggle_label()

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
        self.tray_icon.setIcon(get_app_icon())
        self.tray_icon.setToolTip(strings.APP_TITLE)
        
        tray_menu = QMenu()
        show_action = tray_menu.addAction("🖥️ إظهار التطبيق" if strings.is_ar else "🖥️ Show App")
        show_action.triggered.connect(self.show_normal_and_activate)

        quick_add_action = tray_menu.addAction("⚡ تحميل سريع من الحافظة" if strings.is_ar else "⚡ Quick Add from Clipboard")
        quick_add_action.triggered.connect(self.quick_download_from_clipboard)
        
        tray_menu.addSeparator()

        quit_action = tray_menu.addAction("❌ إغلاق التطبيق نهائياً" if strings.is_ar else "❌ Quit App")
        quit_action.triggered.connect(QApplication.instance().quit)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def show_normal_and_activate(self):
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def quick_download_from_clipboard(self):
        clipboard = QApplication.clipboard()
        text = clipboard.text().strip()
        
        if text.startswith("http"):
            self.show_normal_and_activate()
            self.switch_tab(0)
            self.tab_home.url_input.setText(text)
            self.tab_home.fetch_video_info()
        else:
            QMessageBox.warning(self, "تنبيه" if strings.is_ar else "Warning", 
                                "لا يوجد رابط صالح في الحافظة!" if strings.is_ar else "No valid link in clipboard!")

    def closeEvent(self, event):
        event.accept()
        QApplication.instance().quit()

