from utils.logger import logger
import os
import sys
import json
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QStackedWidget, QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QIcon, QFont
from gui.pages.search_page import SearchPage
from gui.pages.downloads_page import DownloadsPage
from gui.pages.history_page import HistoryPage
from gui.pages.settings_page import SettingsPage
from core.downloader import DownloadWorker
from gui.components.buttons import DownloadProgressButton, NotificationBellButton, NetworkSpeedWidget
from gui.components.dialogs import NotificationsPopup, DownloadsPopup, InteractiveToast
from utils.helpers import resource_path, get_colored_icon, get_current_theme_color, get_data_path, get_masked_app_icon
from utils.locales import tr                                 
from utils.theme import get_style_sheet, get_accent_hex                                            

class VideoDownloader(QWidget):

    def __init__(self):
        super().__init__()
        from managers.settings_manager import SettingsManager
        from utils.theme import ThemeManager
        from managers.history_manager import HistoryManager
        from managers.notification_manager import NotificationManager
        from managers.download_manager import DownloadManager
        from managers.network_manager import NetworkManager

        self.settings_manager = SettingsManager()
        self.network_manager = NetworkManager(self)
        self.network_manager.status_changed.connect(lambda _: self.update_global_progress_ui())
        self.network_manager.start_polling(3000)
        self.theme_manager = ThemeManager(self.settings_manager)
        self.history_manager = HistoryManager()
        self.notification_manager = NotificationManager(self.settings_manager)
        self.download_manager = DownloadManager(self.settings_manager, self.network_manager)
        
        from managers.ui_manager import UIManager
        from managers.system_manager import SystemManager
        self.ui_manager = UIManager(self)
        self.system_manager = SystemManager(self)

        self.is_playlist_mode = False
        self.selected_playlist_entries = []
        self.settings_file = self.settings_manager.settings_file
        self.notifications_list = self.notification_manager.notifications_list
        self.pending_subtitle_reports = []
        self.pending_fallback_reports = []
        self.last_save_dir = self.settings_manager.get("last_save_dir")
        self.sidebar_expanded = True
        self.bypass_close_event = False
        self.is_exiting = False
        self.initUI()

    def initUI(self):
        self.setWindowTitle('AHS-MediaDL')
        icon_path = resource_path(os.path.join('assets', 'icon.ico'))
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.resize(1000, 720) 
        self.setMinimumSize(880, 580)

        self.tray_icon = QSystemTrayIcon(self)
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        self.tray_icon.setToolTip('AHS-MediaDL')

        from PyQt6.QtWidgets import QMenu
        self.tray_menu = QMenu(self)
        self.action_restore = self.tray_menu.addAction(tr("tray_restore", "Restore Window"))
        self.action_restore.triggered.connect(self.restore_window)
        self.tray_menu.addSeparator()
        self.action_exit = self.tray_menu.addAction(tr("tray_exit", "Exit Application"))
        self.action_exit.triggered.connect(self.quit_application)
        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

        window_layout = QVBoxLayout(self)
        window_layout.setContentsMargins(0, 0, 0, 0)
        window_layout.setSpacing(0)
        self.main_stack = QStackedWidget()
        window_layout.addWidget(self.main_stack)
        self.main_app_widget = QWidget()
        app_layout = QHBoxLayout(self.main_app_widget)
        app_layout.setContentsMargins(0, 0, 0, 0)
        app_layout.setSpacing(0)
        self.sidebar = QWidget()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(215)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(10, 12, 8, 12)
        sidebar_layout.setSpacing(8)
        self.header_widget = QWidget()
        self.header_widget.setFixedHeight(52)
        self.header_widget.setStyleSheet("background: transparent; border: none;")
        self.header_layout = QHBoxLayout(self.header_widget)
        self.header_layout.setContentsMargins(2, 2, 2, 2)
        self.header_layout.setSpacing(8)
        
        self.lbl_logo = QLabel()
        self.lbl_logo.setFixedSize(34, 34)
        self.lbl_logo.setScaledContents(True)
        self.lbl_logo.setStyleSheet("background: transparent; border: none;")
        self.lbl_logo.setPixmap(get_masked_app_icon(34, 8))
        self.lbl_logo.setToolTip("AHS-MediaDL — Click to toggle sidebar")
        self.lbl_logo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lbl_logo.mousePressEvent = lambda e: self.logo_clicked()
        self.header_layout.addWidget(self.lbl_logo, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        self.logo_text = QLabel("AHS-MediaDL")
        self.logo_text.setStyleSheet(f"color: {get_accent_hex()}; font-size: 16px; font-weight: 800; background: transparent; border: none;")
        self.header_layout.addWidget(self.logo_text)
        from PyQt6.QtWidgets import QSizePolicy
        self.header_spacer = QWidget()
        self.header_spacer.setStyleSheet("background: transparent; border: none;")
        self.header_spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.header_layout.addWidget(self.header_spacer)
        self.btn_menu = QPushButton()
        self.btn_menu.setObjectName("btn_menu")
        self.btn_menu.setIcon(get_colored_icon("assets/icons/collapse.svg", get_current_theme_color()))
        self.btn_menu.setIconSize(QSize(16, 16))
        self.btn_menu.setFixedSize(28, 28)
        self.btn_menu.clicked.connect(self.ui_manager.toggle_sidebar)
        self.header_layout.addWidget(self.btn_menu)
        sidebar_layout.addWidget(self.header_widget)
        sidebar_layout.addSpacing(10)
        icon_color = get_current_theme_color()
        accent_color = get_accent_hex()
        self.btn_nav_home = QPushButton(tr("nav_home", "Dashboard"))
        self.btn_nav_home.setIcon(get_colored_icon("assets/icons/search-lens.svg", accent_color))
        self.btn_nav_home.setIconSize(QSize(20, 20))
        self.btn_nav_home.setFixedHeight(42)
        self.btn_nav_home.setCheckable(True)
        self.btn_nav_home.setChecked(True)
        self.btn_nav_home.setToolTip(tr("nav_home"))
        self.btn_nav_home.clicked.connect(lambda: self.ui_manager.change_page(0))
        self.btn_nav_downloads = QPushButton(tr("nav_downloads", "Downloads"))
        self.btn_nav_downloads.setIcon(get_colored_icon("assets/icons/download.svg", icon_color))
        self.btn_nav_downloads.setIconSize(QSize(20, 20))
        self.btn_nav_downloads.setFixedHeight(42)
        self.btn_nav_downloads.setCheckable(True)
        self.btn_nav_downloads.setToolTip(tr("nav_downloads"))
        self.btn_nav_downloads.clicked.connect(lambda: self.ui_manager.change_page(1))
        self.btn_nav_history = QPushButton(tr("nav_history", "History"))
        self.btn_nav_history.setIcon(get_colored_icon("assets/icons/history.svg", icon_color))
        self.btn_nav_history.setIconSize(QSize(20, 20))
        self.btn_nav_history.setFixedHeight(42)
        self.btn_nav_history.setCheckable(True)
        self.btn_nav_history.setToolTip(tr("nav_history"))
        self.btn_nav_history.clicked.connect(lambda: self.ui_manager.change_page(2))
        sidebar_layout.addWidget(self.btn_nav_home)
        sidebar_layout.addWidget(self.btn_nav_downloads)
        sidebar_layout.addWidget(self.btn_nav_history)
        sidebar_layout.addStretch()
        self.btn_nav_settings = QPushButton(tr("nav_settings", "Settings"))
        self.btn_nav_settings.setIcon(get_colored_icon("assets/icons/settings.svg", icon_color))
        self.btn_nav_settings.setIconSize(QSize(20, 20))
        self.btn_nav_settings.setFixedHeight(42)
        self.btn_nav_settings.setCheckable(True)
        self.btn_nav_settings.setToolTip(tr("nav_settings"))
        self.btn_nav_settings.clicked.connect(lambda: self.ui_manager.change_page(3))
        sidebar_layout.addWidget(self.btn_nav_settings)
        sidebar_layout.addSpacing(10)
        app_layout.addWidget(self.sidebar)
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(15, 10, 15, 15)
        content_layout.setSpacing(10)
        self.top_header_bar = QWidget()
        self.top_header_bar.setFixedHeight(50)
        self.top_header_bar.setObjectName("TopHeaderBar")
        self.top_header_bar.setStyleSheet("""
            QWidget#TopHeaderBar {
                background: transparent;
                border-bottom: 1px solid rgba(59, 130, 246, 0.18);
            }
        """)
        top_header_layout = QHBoxLayout(self.top_header_bar)
        top_header_layout.setContentsMargins(5, 5, 5, 5)
        top_header_layout.setSpacing(10)
        self.page_title_lbl = QLabel(tr("nav_home"))
        self.page_title_lbl.setObjectName("PageTitleLabel")
        self.page_title_lbl.setStyleSheet("""
            QLabel#PageTitleLabel {
                font-size: 20px;
                font-weight: bold;
            }
        """)
        top_header_layout.addWidget(self.page_title_lbl)
        top_header_layout.addStretch()
        self.btn_network_speed = NetworkSpeedWidget(self)
        self.btn_network_speed.clicked.connect(self.show_network_stats_dialog)
        top_header_layout.addWidget(self.btn_network_speed)
        self.btn_dl_progress = DownloadProgressButton(self)
        self.btn_dl_progress.setIcon(get_colored_icon("assets/icons/download.svg", get_current_theme_color()))
        self.btn_dl_progress.setIconSize(QSize(18, 18))
        self.btn_dl_progress.setToolTip(tr("active_downloads_summary", "Downloads Progress"))
        self.btn_dl_progress.clicked.connect(self.show_downloads_popup)
        top_header_layout.addWidget(self.btn_dl_progress)
        self.btn_bell = NotificationBellButton(self)
        self.btn_bell.setIcon(get_colored_icon("assets/icons/bell.svg", get_current_theme_color()))
        self.btn_bell.setIconSize(QSize(18, 18))
        self.btn_bell.setToolTip(tr("notifications_title", "Notifications"))
        self.btn_bell.clicked.connect(self.show_bell_popup)
        top_header_layout.addWidget(self.btn_bell)
        content_layout.addWidget(self.top_header_bar)
        self.pages_stack = QStackedWidget()
        content_layout.addWidget(self.pages_stack)
        app_layout.addWidget(content_container)
        self.page_search = SearchPage(self)
        self.page_downloads = DownloadsPage(self)
        self.page_history = HistoryPage(self)
        self.page_settings = SettingsPage(self)
        self.cards_layout = self.page_downloads.cards_layout
        self.pages_stack.addWidget(self.page_search)
        self.pages_stack.addWidget(self.page_downloads)
        self.pages_stack.addWidget(self.page_history)
        from gui.pages.onboarding_page import OnboardingPage
        self.page_onboarding = OnboardingPage(self)
        self.main_stack.addWidget(self.main_app_widget)                                      
        self.main_stack.addWidget(self.page_settings)
        self.main_stack.addWidget(self.page_onboarding)
        
        theme_mode = self.settings_manager.get("theme", "auto")
        font_family = self.settings_manager.get("font_family", "System Default")
        font_size = self.settings_manager.get("font_size", 12)
        self.apply_appearance(theme_mode, font_family, font_size)
        self.ui_manager.change_page(0, animate=False) 
        self.global_progress_timer = QTimer(self)
        self.global_progress_timer.timeout.connect(self.update_global_progress_ui)
        self.global_progress_timer.start(500)
        
        first_launch = self.settings_manager.get("first_launch", True)
        if first_launch:
            self.main_stack.setCurrentWidget(self.page_onboarding)
        else:
            self.main_stack.setCurrentWidget(self.main_app_widget)
            
        QTimer.singleShot(200, self.load_incomplete_downloads)
        
        # Clipboard monitoring for foreground app
        self.last_monitored_url = ""
        clipboard = QApplication.clipboard()
        clipboard.dataChanged.connect(self.system_manager.on_clipboard_changed)

    def resizeEvent(self, event):
        super().resizeEvent(event)

    def show_network_stats_dialog(self):
        if not hasattr(self, 'network_stats_dialog'):
            from gui.components.dialogs import NetworkStatsDialog
            self.network_stats_dialog = NetworkStatsDialog(self)
        
        from PyQt6.QtCore import QPoint
        btn_pos = self.btn_network_speed.mapToGlobal(QPoint(0, self.btn_network_speed.height()))
        dialog_x = btn_pos.x() - self.network_stats_dialog.width() + self.btn_network_speed.width()
        dialog_y = btn_pos.y() + 5
        self.network_stats_dialog.move(dialog_x, dialog_y)
        
        if self.network_stats_dialog.isVisible():
            self.network_stats_dialog.hide()
        else:
            self.network_stats_dialog.show()
            self.network_stats_dialog.raise_()
            self.network_stats_dialog.activateWindow()

    def logo_clicked(self):
        self.ui_manager.toggle_sidebar()


    def _refresh_nav_icons(self):
        """يلوّن أيقونات الـ sidebar: الـ active بالأكسنت والباقي بلون الثيم."""
        icon_color = get_current_theme_color()
        accent_color = get_accent_hex()
        nav_map = [
            (self.btn_nav_home,      "assets/icons/search-lens.svg"),
            (self.btn_nav_downloads, "assets/icons/download.svg"),
            (self.btn_nav_history,   "assets/icons/history.svg"),
            (self.btn_nav_settings,  "assets/icons/settings.svg"),
        ]
        for btn, icon_path in nav_map:
            color = accent_color if btn.isChecked() else icon_color
            btn.setIcon(get_colored_icon(icon_path, color))

    def load_incomplete_downloads(self):
        inc_file = get_data_path(os.path.join('data', 'incomplete_downloads.json'))
        if not os.path.exists(inc_file):
            return
        try:
            with open(inc_file, 'r', encoding='utf-8') as f:
                incomplete = json.load(f)
            
            try:
                os.remove(inc_file)
            except:
                pass

            if not incomplete:
                return

            from gui.components.cards import DownloadCard
            from core.downloader import DownloadWorker
            
            self.ui_manager.change_page(1)
            
            for item in incomplete:
                url = item.get('url')
                format_code = item.get('format_code')
                save_path = item.get('save_path')
                sub_lang = item.get('sub_lang')
                is_playlist_sub = item.get('is_playlist_sub', False)
                title = item.get('title', 'Video')
                media_type = item.get('media_type', 'video')
                duration = item.get('duration', '00:00')
                
                new_card = DownloadCard(title, None, save_path)
                new_card.url = url
                new_card.format_code = format_code
                new_card.sub_lang = sub_lang
                new_card.is_playlist_sub = is_playlist_sub
                new_card.media_type = media_type
                new_card.duration = duration
                
                self.cards_layout.insertWidget(0, new_card)
                
                worker = DownloadWorker(url, format_code, save_path, sub_lang=sub_lang, is_playlist_sub=is_playlist_sub)
                worker.progress_signal.connect(new_card.update_progress)
                worker.status_signal.connect(new_card.update_status)
                worker.finished_signal.connect(new_card.set_save_path)
                worker.sub_notification_signal.connect(self.handle_subtitle_notification)
                new_card.set_worker(worker)
                
                new_card.btn_reload.clicked.connect(
                    lambda checked=False, c=new_card, u=url, f=format_code, s=save_path, sb=sub_lang, ips=is_playlist_sub:
                    self.download_manager.reload_download(c, u, f, s, sb, ips)
                )
                
                self.download_manager.waiting_workers.append(worker)
                new_card.update_status(tr("status_waiting_queue", "⏳ Waiting in queue..."))
                
            self.download_manager.process_queue()
        except Exception as e:
            logger.warning(f"Error loading incomplete downloads: {e}")

    def load_settings(self):
        return self.settings_manager.get("last_save_dir", os.path.expanduser("~"))

    def save_settings(self, path):
        self.last_save_dir = path
        self.settings_manager.set("last_save_dir", path)

    def restore_window(self):
        self.showNormal()
        self.activateWindow()
        self.raise_()
        if sys.platform == 'win32':
            try:
                import ctypes
                hwnd = int(self.winId())
                ctypes.windll.user32.ShowWindow(hwnd, 9) # 9 = SW_RESTORE
                ctypes.windll.user32.SetForegroundWindow(hwnd)
            except Exception:
                pass

    def toggle_window_visibility(self):
        if self.isVisible() and not self.isMinimized():
            self.hide()
            from utils.helpers import trim_working_set_memory
            trim_working_set_memory()
        else:
            self.restore_window()

    def on_tray_activated(self, reason):
        from PyQt6.QtWidgets import QSystemTrayIcon
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.toggle_window_visibility()

    def quit_application(self):
        self.bypass_close_event = True
        self.close()
        from PyQt6.QtWidgets import QApplication
        QApplication.quit()



    def handle_incoming_url(self, url):
        self.system_manager.handle_incoming_url(url)

    def show_final_downloads_report(self):
        if not self.pending_subtitle_reports and not self.pending_fallback_reports:
            return
        report_text = ""
        if self.pending_subtitle_reports:
            report_text += tr("report_subtitles_header")
            for title, desc_key, lang_name in self.pending_subtitle_reports:
                if lang_name:
                    desc = tr(desc_key).format(lang=lang_name)
                else:
                    desc = tr(desc_key)
                report_text += f"• {title}:\n  ← {desc}\n\n"
        if self.pending_fallback_reports:
            report_text += tr("report_fallback_header")
            for title, req, down in self.pending_fallback_reports:
                desc = tr("report_fallback_desc").format(req=req, down=down)
                report_text += f"• {title}:\n  ← {desc}\n\n"
        self.pending_subtitle_reports.clear()
        self.pending_fallback_reports.clear()
        from PyQt6.QtWidgets import QMessageBox
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(tr("playlist_detected_title", "تقرير التنزيل النهائي (Download Summary)"))
        msg_box.setText(report_text.strip())
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.button(QMessageBox.StandardButton.Ok).setText(tr("btn_done", "Done"))
        msg_box.show()

    def handle_subtitle_notification(self, type_noti, title, lang_name):
        """ 🔔 معالجة إشعارات الترجمة تم تعطيلها لصالح عرضها مباشرة على البطاقة """
        pass

    def show_notification(self, title, message, icon=None):
        """ إظهار إشعار سطح المكتب للمستخدم عند اكتمال التنزيل (إذا تم تفعيلها) """
        tray = getattr(self, 'tray_icon', None)
        self.notification_manager.add_notification(title, message, tray, icon)
        if hasattr(self, 'btn_bell') and self.btn_bell:
            self.btn_bell.set_has_notifications(self.notification_manager.has_unread())

    def apply_appearance(self, theme_name, font_family="System Default", font_size=12):
        """ تطبيق الثيم ونوع وحجم الخط فوراً ديناميكياً من ملف بايثون الثيمات """
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QFont
        if font_family == "System Default":
            font = QApplication.font()
            font.setPointSize(font_size)
        else:
            font = QFont(font_family, font_size)
        QApplication.setFont(font)
        lang = self.settings_manager.get("language", "system")
        from utils.locales import resolve_lang
        lang = resolve_lang(lang)
        is_rtl = (lang == "ar")
        if is_rtl:
            self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            QApplication.instance().setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        else:
            self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
            QApplication.instance().setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        try:
            qss_content = get_style_sheet(theme_name, font_family, font_size, is_rtl=is_rtl)
            self.setStyleSheet(qss_content)
        except Exception:
            pass
        actual_theme = theme_name
        if theme_name == "auto":
            from utils.helpers import detect_system_theme
            actual_theme = detect_system_theme()
        icon_color = "#f1f5f9" if actual_theme == "dark" else "#0f172a"
        # Refresh nav icons with accent for active button
        self._refresh_nav_icons()
        menu_icon = "assets/icons/collapse.svg" if self.sidebar_expanded else "assets/icons/expand.svg"
        self.btn_menu.setIcon(get_colored_icon(menu_icon, icon_color))
        if hasattr(self, 'btn_dl_progress') and self.btn_dl_progress:
            self.btn_dl_progress.setIcon(get_colored_icon("assets/icons/download.svg", icon_color))
        if hasattr(self, 'btn_bell') and self.btn_bell:
            self.btn_bell.setIcon(get_colored_icon("assets/icons/bell.svg", icon_color))
        if hasattr(self, 'btn_network_speed') and self.btn_network_speed:
            self.btn_network_speed.update_style()
        if hasattr(self, 'lbl_logo') and self.lbl_logo:
            self.lbl_logo.setPixmap(get_masked_app_icon(34, 8))
        if hasattr(self, 'logo_text') and self.logo_text:
            self.logo_text.setStyleSheet(f"color: {get_accent_hex()}; font-size: 16px; font-weight: 800; background: transparent; border: none;")
        if hasattr(self, 'page_search') and hasattr(self.page_search, 'update_icon_colors'):
            self.page_search.update_icon_colors(icon_color)
        if hasattr(self, 'page_downloads') and hasattr(self.page_downloads, 'update_icon_colors'):
            self.page_downloads.update_icon_colors(icon_color)
        if hasattr(self, 'page_history') and hasattr(self.page_history, 'update_icon_colors'):
            self.page_history.update_icon_colors(icon_color)
        if hasattr(self, 'page_settings') and hasattr(self.page_settings, 'update_icon_colors'):
            self.page_settings.update_icon_colors(icon_color)
            
        # Update accent colors
        if hasattr(self, 'page_search') and hasattr(self.page_search, 'update_accent_colors'):
            self.page_search.update_accent_colors()
        if hasattr(self, 'page_downloads') and hasattr(self.page_downloads, 'update_accent_colors'):
            self.page_downloads.update_accent_colors()
        if hasattr(self, 'page_history') and hasattr(self.page_history, 'update_accent_colors'):
            self.page_history.update_accent_colors()
        if hasattr(self, 'page_settings') and hasattr(self.page_settings, 'update_accent_colors'):
            self.page_settings.update_accent_colors()

        if hasattr(self, 'cards_layout') and self.cards_layout:
            for i in range(self.cards_layout.count()):
                widget = self.cards_layout.itemAt(i).widget()
                if widget and hasattr(widget, 'update_icon_colors'):
                    widget.update_icon_colors(icon_color)
        if hasattr(self, 'page_history') and hasattr(self.page_history, 'cards_layout') and self.page_history.cards_layout:
            layout = self.page_history.cards_layout
            for i in range(layout.count()):
                widget = layout.itemAt(i).widget()
                if widget and hasattr(widget, 'update_icon_colors'):
                    widget.update_icon_colors(icon_color)

    def update_app_download_rules(self, data):
        """ تحديث القواعد والحد الأقصى للتحميلات المتزامنة فوراً عند الضغط على حفظ """
        c_type = data.get("concurrent_type", "3")
        if c_type == "custom":
            self.download_manager.max_concurrent = data.get("custom_concurrent_value", 3)
        else:
            self.download_manager.max_concurrent = int(c_type)
        self.download_manager.process_queue()
        self.update_active_speed_limits()

    def update_active_speed_limits(self):
        """ 🧠 إدارة النطاق الترددي التفاعلية من الذاكرة مباشرة دون قراءة القرص """
        limit_bps = None
        speed_type = self.settings_manager.get("speed_limit_type", "unlimited")
        if speed_type == "2M":
            limit_bps = 2 * 1024 * 1024
        elif speed_type == "1M":
            limit_bps = 1024 * 1024
        elif speed_type == "500K":
            limit_bps = 500 * 1024
        elif speed_type == "custom":
            val = self.settings_manager.get("custom_speed_value", 100)
            unit = self.settings_manager.get("custom_speed_unit", "KB")
            mult = 1024 * 1024 if unit == "MB" else 1024
            limit_bps = int(val * mult)

        from PyQt6 import sip
        active = [
            w for w in self.download_manager.active_workers
            if not sip.isdeleted(w) and hasattr(w, 'isRunning') and w.isRunning() and not getattr(w, 'is_paused', False)
        ]
        num_active = len(active)
        if num_active > 0 and limit_bps is not None:
            divided_limit = int(limit_bps / num_active)
            for worker in active:
                worker.update_rate_limit(divided_limit)
        elif num_active > 0:
            for worker in active:
                worker.update_rate_limit(None)

    def show_bell_popup(self):
        self.bell_popup = NotificationsPopup(self, self)
        btn_pos = self.btn_bell.mapToGlobal(self.btn_bell.rect().bottomLeft())
        is_rtl = (self.layoutDirection() == Qt.LayoutDirection.RightToLeft)
        if is_rtl:
            popup_x = btn_pos.x()
        else:
            popup_x = btn_pos.x() - 300 + 32
        popup_y = btn_pos.y() + 5
        self.bell_popup.move(popup_x, popup_y)
        self.bell_popup.show()
        self.btn_bell.set_has_notifications(False)
        self.notification_manager.mark_all_read()

    def show_downloads_popup(self):
        self.downloads_popup = DownloadsPopup(self, self)
        btn_pos = self.btn_dl_progress.mapToGlobal(self.btn_dl_progress.rect().bottomLeft())
        is_rtl = (self.layoutDirection() == Qt.LayoutDirection.RightToLeft)
        if is_rtl:
            popup_x = btn_pos.x()
        else:
            popup_x = btn_pos.x() - 260 + 32
        popup_y = btn_pos.y() + 5
        self.downloads_popup.move(popup_x, popup_y)
        self.downloads_popup.show()

    def update_global_progress_ui(self):
        if not hasattr(self, 'page_downloads') or not hasattr(self, 'btn_dl_progress'):
            return
        self.page_downloads.check_empty_state()
        cards = self.page_downloads.get_download_cards()
        active_count = 0
        total_progress = 0
        for card in cards:
            if hasattr(card, 'p_bar'):
                val = card.p_bar.value()
                # Check if card is currently active (downloading, not paused/completed/canceled/errored)
                is_card_active = val < 100 and getattr(card, 'status_label', None) and not (
                    "Paused" in card.status_label._full_text or 
                    "مؤقتاً" in card.status_label._full_text or 
                    "Canceled" in card.status_label._full_text or 
                    "إلغاء" in card.status_label._full_text or 
                    "Error" in card.status_label._full_text or
                    "خطأ" in card.status_label._full_text or
                    "Completed" in card.status_label._full_text or
                    "تم التنزيل" in card.status_label._full_text
                )
                if is_card_active:
                    total_progress += val
                    active_count += 1
        
        avg_progress = float(total_progress / active_count) if active_count > 0 else 0.0
        if active_count > 0:
            self.btn_dl_progress.set_progress(avg_progress, is_active=True)
        else:
            self.btn_dl_progress.set_progress(0.0, is_active=False)

        # 🌐 تحديث مؤشر حالة شبكة الإنترنت والسرعة الحية
        if hasattr(self, 'btn_network_speed'):
            is_connected = self.network_manager.is_connected
            total_speed_bps = 0.0
            from PyQt6 import sip
            if is_connected and hasattr(self.download_manager, 'active_workers'):
                for worker in self.download_manager.active_workers:
                    if not sip.isdeleted(worker) and hasattr(worker, 'isRunning') and worker.isRunning():
                        total_speed_bps += float(getattr(worker, 'current_speed_bps', 0) or 0)
                        
            from managers.network_manager import NetworkTracker
            tracker = NetworkTracker()
            tracker.set_current_speed(total_speed_bps)
            stats = tracker.get_stats()
            self.btn_network_speed.update_speed(is_connected, stats.get("rx_speed", 0))
            self.update_active_speed_limits()



    def retranslate_app(self):
        from utils.locales import set_current_language, resolve_lang, tr
        lang = self.settings_manager.get("language", "system")
        set_current_language(lang)
        
        actual_lang = resolve_lang(lang)
        is_rtl = (actual_lang == "ar")
        direction = Qt.LayoutDirection.RightToLeft if is_rtl else Qt.LayoutDirection.LeftToRight
        self.setLayoutDirection(direction)
        QApplication.instance().setLayoutDirection(direction)
        
        if self.sidebar_expanded:
            self.btn_nav_home.setText(tr("nav_home"))
            self.btn_nav_downloads.setText(tr("nav_downloads"))
            self.btn_nav_history.setText(tr("nav_history"))
            self.btn_nav_settings.setText(tr("nav_settings"))
        else:
            self.btn_nav_home.setText("")
            self.btn_nav_downloads.setText("")
            self.btn_nav_history.setText("")
            self.btn_nav_settings.setText("")
            
        self.btn_nav_home.setToolTip(tr("nav_home"))
        self.btn_nav_downloads.setToolTip(tr("nav_downloads"))
        self.btn_nav_history.setToolTip(tr("nav_history"))
        self.btn_nav_settings.setToolTip(tr("nav_settings"))
        
        if hasattr(self, 'action_restore') and self.action_restore:
            self.action_restore.setText(tr("tray_restore", "Restore Window"))
        if hasattr(self, 'action_exit') and self.action_exit:
            self.action_exit.setText(tr("tray_exit", "Exit Application"))

        for page in [getattr(self, 'page_search', None), getattr(self, 'page_downloads', None), getattr(self, 'page_history', None), getattr(self, 'page_settings', None), getattr(self, 'page_onboarding', None)]:
            if page and hasattr(page, 'retranslate_ui'):
                try:
                    page.retranslate_ui()
                except Exception:
                    pass

    def finish_onboarding(self):
        self.retranslate_app()
        self.main_stack.setCurrentWidget(self.main_app_widget)

    def closeEvent(self, event):
        run_in_background = self.settings_manager.get("run_in_background", False)
        if run_in_background and not getattr(self, 'bypass_close_event', False):
            event.ignore()
            self.hide()
            from utils.helpers import trim_working_set_memory
            trim_working_set_memory()
            return

        # 1. Save truly incomplete downloads (exclude completed, canceled, or errored cards)
        incomplete = []
        from gui.components.cards import DownloadCard
        for i in range(self.cards_layout.count()):
            item = self.cards_layout.itemAt(i)
            if item:
                widget = item.widget()
                if isinstance(widget, DownloadCard):
                    is_finished_or_failed = (
                        not widget.btn_open.isHidden() or
                        not widget.btn_reload.isHidden() or
                        getattr(widget.worker, 'is_cancelled', False)
                    )
                    if not is_finished_or_failed:
                        incomplete.append({
                            'title': widget.title_label._full_text,
                            'url': widget.url,
                            'format_code': widget.format_code,
                            'save_path': widget.save_path,
                            'sub_lang': widget.sub_lang,
                            'is_playlist_sub': widget.is_playlist_sub,
                            'media_type': getattr(widget, 'media_type', 'video'),
                            'duration': getattr(widget, 'duration', '00:00')
                        })
        
        inc_file = get_data_path(os.path.join('data', 'incomplete_downloads.json'))
        try:
            if incomplete:
                with open(inc_file, 'w', encoding='utf-8') as f:
                    json.dump(incomplete, f, ensure_ascii=False, indent=4)
            else:
                if os.path.exists(inc_file):
                    os.remove(inc_file)
        except Exception as e:
            logger.warning(f"Error saving incomplete downloads: {e}")

        # 2. Stop all active download threads and FFmpeg processes cleanly
        if hasattr(self, 'download_manager'):
            self.download_manager.cancel_all()

        # 3. Stop timers and IPC server
        if hasattr(self, 'network_manager'):
            self.network_manager.stop_polling()
        if hasattr(self, 'global_progress_timer') and self.global_progress_timer.isActive():
            self.global_progress_timer.stop()
        if hasattr(self, '_ipc_server'):
            self._ipc_server.close()
        if hasattr(self, 'tray_icon'):
            self.tray_icon.hide()

        event.accept()
        QApplication.quit()


