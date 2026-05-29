import os
import sys
import json
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QStackedWidget, QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QIcon, QFont
from gui.pages.home_page import HomePage
from gui.pages.downloads_page import DownloadsPage
from gui.pages.history_page import HistoryPage
from gui.pages.settings_page import SettingsPage
from core.downloader import DownloadWorker
from gui.widgets import DownloadProgressButton, NotificationBellButton, NotificationsPopup, DownloadsPopup, InteractiveToast
from utils.helpers import resource_path, get_colored_icon, get_current_theme_color
from utils.locales import tr                                 
from utils.theme import get_style_sheet                                            

class VideoDownloader(QWidget):

    def __init__(self):
        super().__init__()
        self.is_playlist_mode = False
        self.selected_playlist_entries = []
        self.settings_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'settings.json')
        self.notifications_list = []
        self.pending_subtitle_reports = []
        self.pending_fallback_reports = []
        self.last_save_dir = self.load_settings()
        self.sidebar_expanded = True                                 
        self.is_paused_by_network = False
        self.hotkey_registered = False
        self.bypass_close_event = False
        self.last_monitored_url = ""
        self.initUI()
        self.register_global_hotkey()
        clipboard = QApplication.clipboard()
        clipboard.dataChanged.connect(self.on_clipboard_changed)

    def initUI(self):
        self.setWindowTitle('AHS-MediaDL')
        self.setWindowIcon(QIcon(resource_path(os.path.join('assets', 'icon.ico'))))
        self.resize(880, 640) 
        self.setMinimumSize(700, 480)
        self.max_concurrent = 3
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    c_type = config_data.get("concurrent_type", "3")
                    self.max_concurrent = config_data.get("custom_concurrent_value", 3) if c_type == "custom" else int(c_type)
            except Exception:
                pass
        self.active_workers = []
        self.waiting_workers = []
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(resource_path(os.path.join('assets', 'icon.ico'))))
        self.tray_menu = QMenu()
        self.restore_action = self.tray_menu.addAction(tr("tray_restore", "Restore Window"))
        self.restore_action.triggered.connect(self.restore_window)
        self.exit_action = self.tray_menu.addAction(tr("tray_exit", "Exit Application"))
        self.exit_action.triggered.connect(self.exit_application_completely)
        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()
        self.register_start_menu_shortcut()
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
        self.sidebar.setStyleSheet("QWidget#Sidebar { border-right: 1px solid rgba(128, 128, 128, 0.2); }")
        self.sidebar.setFixedWidth(180) 
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(5, 5, 5, 5)
        sidebar_layout.setSpacing(10)
        self.header_widget = QWidget()
        self.header_widget.setFixedHeight(45)
        self.header_layout = QHBoxLayout(self.header_widget)
        self.header_layout.setContentsMargins(5, 0, 5, 0)
        self.header_layout.setSpacing(8)
        self.btn_logo = QPushButton()
        self.btn_logo.setIcon(QIcon(resource_path("assets/icon.ico")))
        self.btn_logo.setIconSize(QSize(32, 32))
        self.btn_logo.setFixedSize(32, 32)
        self.btn_logo.setFlat(True)
        self.btn_logo.setStyleSheet("background: transparent; border: none; padding: 0px;")
        self.btn_logo.clicked.connect(self.logo_clicked)
        self.header_layout.addWidget(self.btn_logo)
        self.logo_text = QLabel("MediaDL")
        self.logo_text.setStyleSheet("color: #ff5e3a; font-size: 16px; font-weight: bold; background: transparent; border: none;")
        self.header_layout.addWidget(self.logo_text)
        from PyQt6.QtWidgets import QSizePolicy
        self.header_spacer = QWidget()
        self.header_spacer.setStyleSheet("background: transparent; border: none;")
        self.header_spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.header_layout.addWidget(self.header_spacer)
        self.btn_menu = QPushButton()
        self.btn_menu.setObjectName("btn_menu")
        self.btn_menu.setIcon(get_colored_icon("assets/icons/collapse.svg", get_current_theme_color()))
        self.btn_menu.setIconSize(QSize(18, 18))
        self.btn_menu.setFixedSize(30, 30)
        self.btn_menu.clicked.connect(self.toggle_sidebar)
        self.header_layout.addWidget(self.btn_menu)
        sidebar_layout.addWidget(self.header_widget)
        self.btn_nav_home = QPushButton(tr("nav_home"))
        self.btn_nav_home.setIcon(get_colored_icon("assets/icons/home.svg", get_current_theme_color()))
        self.btn_nav_home.setIconSize(QSize(20, 20))
        self.btn_nav_home.setCheckable(True)
        self.btn_nav_home.setChecked(True) 
        self.btn_nav_home.clicked.connect(lambda: self.change_page(0))
        self.btn_nav_downloads = QPushButton(tr("nav_downloads"))
        self.btn_nav_downloads.setIcon(get_colored_icon("assets/icons/download.svg", get_current_theme_color()))
        self.btn_nav_downloads.setIconSize(QSize(20, 20))
        self.btn_nav_downloads.setCheckable(True)
        self.btn_nav_downloads.clicked.connect(lambda: self.change_page(1))
        self.btn_nav_history = QPushButton(tr("nav_history"))
        self.btn_nav_history.setIcon(get_colored_icon("assets/icons/history.svg", get_current_theme_color()))
        self.btn_nav_history.setIconSize(QSize(20, 20))
        self.btn_nav_history.setCheckable(True)
        self.btn_nav_history.clicked.connect(lambda: self.change_page(2))
        sidebar_layout.addWidget(self.btn_nav_home)
        sidebar_layout.addWidget(self.btn_nav_downloads)
        sidebar_layout.addWidget(self.btn_nav_history)
        sidebar_layout.addStretch()
        self.btn_nav_settings = QPushButton(tr("nav_settings"))
        self.btn_nav_settings.setIcon(get_colored_icon("assets/icons/settings.svg", get_current_theme_color()))
        self.btn_nav_settings.setIconSize(QSize(20, 20))
        self.btn_nav_settings.setCheckable(True)
        self.btn_nav_settings.clicked.connect(lambda: self.change_page(3)) 
        sidebar_layout.addWidget(self.btn_nav_settings)
        sidebar_layout.addSpacing(15)                                                                    
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
                border-bottom: 1px solid rgba(128, 128, 128, 0.15);
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
        self.page_home = HomePage(self) 
        self.page_downloads = DownloadsPage(self) 
        self.page_history = HistoryPage(self)
        self.page_settings = SettingsPage(self) 
        self.cards_layout = self.page_downloads.cards_layout 
        self.pages_stack.addWidget(self.page_home)
        self.pages_stack.addWidget(self.page_downloads)
        self.pages_stack.addWidget(self.page_history)
        self.main_stack.addWidget(self.main_app_widget)                                      
        self.main_stack.addWidget(self.page_settings)                                        
        applied = False
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.apply_appearance(data.get("theme", "auto"), data.get("font_family", "System Default"), data.get("font_size", 12))
                    applied = True
            except Exception:
                pass
        if not applied:
            self.apply_appearance("auto", "System Default", 12)
        self.change_page(0) 
        self.global_progress_timer = QTimer(self)
        self.global_progress_timer.timeout.connect(self.update_global_progress_ui)
        self.global_progress_timer.start(500)
        self.reconnection_timer = QTimer(self)
        self.reconnection_timer.timeout.connect(self.check_reconnection)
        first_launch = False
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    first_launch = config.get("first_launch", True)
            except Exception:
                pass
        if first_launch:
            QTimer.singleShot(1500, self.run_sidebar_teaser_animation)
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                config["first_launch"] = False
                with open(self.settings_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=4)
            except Exception:
                pass

    def logo_clicked(self):
        self.toggle_sidebar()

    def toggle_sidebar(self):
        icon_color = get_current_theme_color()
        is_rtl = (self.layoutDirection() == Qt.LayoutDirection.RightToLeft)
        if self.sidebar_expanded:
            self.sidebar.setFixedWidth(60)
            self.logo_text.hide()
            self.btn_logo.show()                                                     
            self.header_spacer.hide()
            self.btn_menu.hide()                                                            
            self.btn_nav_home.setText("")
            self.btn_nav_downloads.setText("")
            self.btn_nav_history.setText("")
            self.btn_nav_settings.setText("")
            self.header_layout.setContentsMargins(0, 0, 0, 0)
            self.header_layout.setAlignment(self.btn_logo, Qt.AlignmentFlag.AlignCenter)                                       
            self.sidebar_expanded = False
        else:
            self.sidebar.setFixedWidth(180)
            self.logo_text.show()
            self.btn_logo.show()
            self.header_spacer.show()
            self.btn_menu.show()                                                          
            self.btn_nav_home.setText(tr("nav_home"))
            self.btn_nav_downloads.setText(tr("nav_downloads"))
            self.btn_nav_history.setText(tr("nav_history"))
            self.btn_nav_settings.setText(tr("nav_settings"))
            self.header_layout.setContentsMargins(5, 0, 5, 0)
            self.header_layout.setAlignment(self.btn_logo, Qt.AlignmentFlag.AlignVCenter)
            self.header_layout.setAlignment(self.btn_menu, Qt.AlignmentFlag.AlignVCenter)
            collapse_icon = "expand.svg" if is_rtl else "collapse.svg"
            self.btn_menu.setIcon(get_colored_icon(f"assets/icons/{collapse_icon}", icon_color))
            self.sidebar_expanded = True

    def change_page(self, index):
        if index == 3:
            self.main_stack.setCurrentIndex(1)
            self.btn_nav_settings.setChecked(True)
            self.btn_nav_home.setChecked(False)
            self.btn_nav_downloads.setChecked(False)
            self.btn_nav_history.setChecked(False)
        else:
            self.main_stack.setCurrentIndex(0)
            self.pages_stack.setCurrentIndex(index)
            self.btn_nav_home.setChecked(index == 0)
            self.btn_nav_downloads.setChecked(index == 1)
            self.btn_nav_history.setChecked(index == 2)
            self.btn_nav_settings.setChecked(False)
            if hasattr(self, 'page_title_lbl'):
                if index == 0:
                    self.page_title_lbl.setText(tr("nav_home"))
                elif index == 1:
                    self.page_title_lbl.setText(tr("nav_downloads"))
                elif index == 2:
                    self.page_title_lbl.setText(tr("nav_history"))
            if index == 2 and hasattr(self, 'page_history'):
                self.page_history.load_history_ui()

    def load_settings(self):
        os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
        if not os.path.exists(self.settings_file):
            default_data = {
                "last_save_dir": os.path.join(os.path.expanduser("~"), "Downloads"),
                "language": "system",
                "notifications": True,
                "theme": "auto",
                "font_family": "System Default",
                "scaling": "auto",
                "font_size": 12,
                "download_path_type": "downloads",
                "custom_path": "",
                "speed_limit_type": "unlimited",
                "custom_speed_value": 100,
                "custom_speed_unit": "KB",
                "concurrent_type": "3",
                "custom_concurrent_value": 3,
                "primary_sub_lang": "ar",
                "secondary_sub_lang": "en",
                "download_any_sub_fallback": True,
                "video_container": "mp4",
                "embed_subtitles": True,
                "autoplay_subtitles": True,
                "external_sub_format": "srt",
                "audio_sub_format": "lrc",
                "embed_audio_sub": True,
                "audio_container": "m4a",
                "quality_fallback": True,
                "first_launch": True,
                "run_in_background": True,
                "clipboard_monitor": True
            }
            try:
                with open(self.settings_file, 'w', encoding='utf-8') as f:
                    json.dump(default_data, f, ensure_ascii=False, indent=4)
            except Exception:
                pass
        try:
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("last_save_dir", os.path.expanduser("~"))
        except Exception:
            pass
        return os.path.expanduser("~")

    def save_settings(self, path):
        os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
        data = {}
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception:
                pass
        data["last_save_dir"] = path
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception:
            pass

    def reload_download(self, card, url, format_code, save_path, sub_lang=None, is_playlist_sub=False):
        if hasattr(card, 'worker') and card.worker:
            old_worker = card.worker
            from PyQt6 import sip
            if not sip.isdeleted(old_worker):
                if old_worker in self.active_workers:
                    self.active_workers.remove(old_worker)
                if old_worker in self.waiting_workers:
                    self.waiting_workers.remove(old_worker)
                try:
                    old_worker.progress_signal.disconnect()
                    old_worker.status_signal.disconnect()
                    old_worker.finished_signal.disconnect()
                    old_worker.finished.disconnect(self.on_worker_finished)
                except:
                    pass
                try:
                    if old_worker.isRunning():
                        old_worker.cancel()
                        old_worker.quit()
                        old_worker.finished.connect(old_worker.deleteLater)
                    else:
                        old_worker.deleteLater()
                except RuntimeError:
                    pass
        card.status_label.setText(tr("status_waiting_queue"))
        card.p_bar.setValue(0)
        card.btn_reload.hide()
        card.btn_open.hide()
        card.btn_pause.setToolTip("Pause")
        card.btn_pause.show()
        card.btn_cancel.show()
        worker = DownloadWorker(url, format_code, save_path, sub_lang, is_playlist_sub)
        worker.progress_signal.connect(card.update_progress)
        worker.status_signal.connect(card.update_status)
        worker.finished_signal.connect(card.set_save_path)
        worker.sub_notification_signal.connect(self.handle_subtitle_notification)
        card.set_worker(worker)
        self.waiting_workers.insert(0, worker)
        self.process_queue()

    def process_queue(self):
        while len(self.active_workers) < self.max_concurrent and self.waiting_workers:
            worker = self.waiting_workers.pop(0) 
            self.active_workers.append(worker)   
            worker.finished.connect(self.on_worker_finished)
            worker.start() 
        self.update_active_speed_limits()

    def is_internet_available(self):
        import socket
        try:
            socket.setdefaulttimeout(3)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
            return True
        except Exception:
            return False

    def register_start_menu_shortcut(self):
        if sys.platform != 'win32':
            return
        try:
            import subprocess
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            icon_path = os.path.join(app_dir, 'assets', 'icon.ico')
            shortcut_path = os.path.join(os.environ['APPDATA'], 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'AHS-MediaDL.lnk')
            if not os.path.exists(shortcut_path):
                target = sys.executable
                arguments = f'"{os.path.join(app_dir, "main.py")}"'
                cmd = f'powershell -WindowStyle Hidden -Command "$w=New-Object -ComObject WScript.Shell;$s=$w.CreateShortcut(\'{shortcut_path}\');$s.TargetPath=\'{target}\';$s.Arguments=\'{arguments}\';$s.WorkingDirectory=\'{app_dir}\';$s.IconLocation=\'{icon_path}\';$s.Save()"'
                subprocess.Popen(cmd, shell=True)
        except Exception:
            pass

    def check_reconnection(self):
        if self.is_internet_available():
            self.reconnection_timer.stop()
            self.is_paused_by_network = False
            if hasattr(self, 'page_downloads'):
                for card in self.page_downloads.get_download_cards():
                    if getattr(card, 'failed_due_to_connection', False):
                        card.failed_due_to_connection = False
                        if hasattr(card, 'btn_reload'):
                            card.btn_reload.click()
            self.process_queue()

    def on_worker_finished(self):
        worker = self.sender() 
        is_conn_err = getattr(worker, 'is_connection_error', False)
        associated_card = None
        if hasattr(self, 'page_downloads'):
            for card in self.page_downloads.get_download_cards():
                if getattr(card, 'worker', None) == worker:
                    associated_card = card
                    break
        if hasattr(worker, 'fallback_detected') and worker.fallback_detected:
            title, req, down = worker.fallback_info
            self.pending_fallback_reports.append((title, req, down))
        if worker in self.active_workers:
            self.active_workers.remove(worker) 
        worker.deleteLater()
        self.update_active_speed_limits()
        if is_conn_err:
            if associated_card:
                associated_card.failed_due_to_connection = True
                associated_card.update_status(tr("status_waiting_internet"))
            if not self.is_internet_available():
                self.is_paused_by_network = True
                if not self.reconnection_timer.isActive():
                    self.reconnection_timer.start(5000)                        
                self.show_notification(tr("confirm_title", "Notification"), tr("status_error_conn"))
        if not self.is_paused_by_network:
            self.process_queue()
        if len(self.active_workers) == 0 and len(self.waiting_workers) == 0 and not self.is_paused_by_network:
            self.show_final_downloads_report()

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
        """ 🔔 معالجة إشعارات الترجمة لقوائم التشغيل بصورة غير حازرة للتحميل (Non-blocking) """
        if type_noti == "secondary":
            tray_msg = tr("tray_sub_secondary").format(lang=lang_name, title=title)
            self.pending_subtitle_reports.append((title, "report_sub_secondary", lang_name))
        elif type_noti == "fallback":
            tray_msg = tr("tray_sub_fallback").format(lang=lang_name, title=title)
            self.pending_subtitle_reports.append((title, "report_sub_fallback", lang_name))
        elif type_noti == "none":
            tray_msg = tr("tray_sub_none").format(title=title)
            self.pending_subtitle_reports.append((title, "report_sub_none", ""))
        else:
            return
        self.show_notification(tr("sub_report_title", "Subtitle Download Report"), tray_msg)

    def show_notification(self, title, message, icon=None):
        """ إظهار إشعار سطح المكتب للمستخدم عند اكتمال التنزيل (إذا تم تفعيلها) """
        from datetime import datetime
        now_str = datetime.now().strftime("%I:%M %p")
        self.notifications_list.insert(0, {
            "title": title,
            "message": message,
            "time": now_str,
            "read": False
        })
        if hasattr(self, 'btn_bell') and self.btn_bell:
            self.btn_bell.set_has_notifications(True)
        notifications_enabled = True
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    notifications_enabled = data.get("notifications", True)
            except Exception:
                pass
        if notifications_enabled:
            from PyQt6.QtGui import QIcon, QPixmap
            if icon is None:
                icon_path = resource_path(os.path.join('assets', 'icon.ico'))
                if os.path.exists(icon_path):
                    icon = QIcon(icon_path)
            if icon is not None:
                if isinstance(icon, QPixmap):
                    qicon = QIcon(icon)
                elif isinstance(icon, QIcon):
                    qicon = icon
                else:
                    qicon = QIcon(icon)
                self.tray_icon.showMessage(
                    title,
                    message,
                    qicon,
                    5000
                )
            else:
                self.tray_icon.showMessage(
                    title,
                    message,
                    QSystemTrayIcon.MessageIcon.Information,
                    5000
                )

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
        lang = "system"
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    lang = data.get("language", "system")
            except Exception:
                pass
        from utils.locales import resolve_lang
        lang = resolve_lang(lang)
        is_rtl = (lang == "ar")
        if is_rtl:
            self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        else:
            self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        try:
            qss_content = get_style_sheet(theme_name, font_family, font_size, is_rtl=is_rtl)
            self.setStyleSheet(qss_content)
        except Exception:
            pass
        actual_theme = theme_name
        if theme_name == "auto":
            from PyQt6.QtGui import QGuiApplication
            scheme = QGuiApplication.styleHints().colorScheme()
            actual_theme = "dark" if scheme == Qt.ColorScheme.Dark else "light"
        icon_color = "#f1f5f9" if actual_theme == "dark" else "#0f172a"
        self.btn_nav_home.setIcon(get_colored_icon("assets/icons/home.svg", icon_color))
        self.btn_nav_downloads.setIcon(get_colored_icon("assets/icons/download.svg", icon_color))
        self.btn_nav_history.setIcon(get_colored_icon("assets/icons/history.svg", icon_color))
        self.btn_nav_settings.setIcon(get_colored_icon("assets/icons/settings.svg", icon_color))
        menu_icon = "assets/icons/collapse.svg" if self.sidebar_expanded else "assets/icons/expand.svg"
        self.btn_menu.setIcon(get_colored_icon(menu_icon, icon_color))
        if hasattr(self, 'btn_dl_progress') and self.btn_dl_progress:
            self.btn_dl_progress.setIcon(get_colored_icon("assets/icons/download.svg", icon_color))
        if hasattr(self, 'btn_bell') and self.btn_bell:
            self.btn_bell.setIcon(get_colored_icon("assets/icons/bell.svg", icon_color))
        if hasattr(self, 'page_home') and hasattr(self.page_home, 'update_icon_colors'):
            self.page_home.update_icon_colors(icon_color)
        if hasattr(self, 'page_downloads') and hasattr(self.page_downloads, 'update_icon_colors'):
            self.page_downloads.update_icon_colors(icon_color)
        if hasattr(self, 'page_history') and hasattr(self.page_history, 'update_icon_colors'):
            self.page_history.update_icon_colors(icon_color)
        if hasattr(self, 'page_settings') and hasattr(self.page_settings, 'update_icon_colors'):
            self.page_settings.update_icon_colors(icon_color)
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
            self.max_concurrent = data.get("custom_concurrent_value", 3)
        else:
            self.max_concurrent = int(c_type)
        self.process_queue()
        self.update_active_speed_limits()

    def update_active_speed_limits(self):
        """ 🧠 إدارة النطاق الترددي التفاعلية: تقسيم وتوزيع حد السرعة الإجمالي بالتساوي على التحميلات النشطة وغير الموقفة مؤقتاً """
        limit_bps = None
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    speed_type = data.get("speed_limit_type", "unlimited")
                    if speed_type == "2M":
                        limit_bps = 2 * 1024 * 1024
                    elif speed_type == "1M":
                        limit_bps = 1024 * 1024
                    elif speed_type == "500K":
                        limit_bps = 500 * 1024
                    elif speed_type == "custom":
                        val = data.get("custom_speed_value", 100)
                        unit = data.get("custom_speed_unit", "KB")
                        mult = 1024 * 1024 if unit == "MB" else 1024
                        limit_bps = int(val * mult)
            except Exception:
                pass
        from PyQt6 import sip
        active = [w for w in self.active_workers if not sip.isdeleted(w) and hasattr(w, 'isRunning') and w.isRunning() and not getattr(w, 'is_paused', False)]
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
        total_count = len(cards)
        total_progress = 0
        for card in cards:
            if hasattr(card, 'p_bar'):
                val = card.p_bar.value()
                total_progress += val
                if val < 100 and getattr(card, 'status_label', None) and not (
                    "Paused" in card.status_label._full_text or 
                    "مؤقتاً" in card.status_label._full_text or 
                    "Canceled" in card.status_label._full_text or 
                    "إلغاء" in card.status_label._full_text or 
                    "Error" in card.status_label._full_text or
                    "خطأ" in card.status_label._full_text
                ):
                    active_count += 1
        avg_progress = float(total_progress / total_count) if total_count > 0 else 0.0
        if active_count > 0:
            self.btn_dl_progress.set_progress(avg_progress, is_active=True)
        else:
            self.btn_dl_progress.set_progress(0.0, is_active=False)

    def run_sidebar_teaser_animation(self):
        if self.sidebar_expanded:
            self.toggle_sidebar()
            QTimer.singleShot(1200, lambda: self.toggle_sidebar() if not self.sidebar_expanded else None)

    def toggle_window_visibility(self):
        if self.isVisible() and not self.isMinimized() and self.isActiveWindow():
            self.hide()
        else:
            self.restore_window()

    def restore_window(self):
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def exit_application_completely(self):
        if hasattr(self, '_ipc_server'):
            self._ipc_server.close()
        self.tray_icon.hide()
        QApplication.quit()

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.restore_window()

    def handle_incoming_url(self, url):
        url = url.strip()
        if url.lower().startswith("dl:"):
            url = url[3:]
        elif url.lower().startswith("dl"):
            url = url[2:]
        url = url.strip()
        self.restore_window()
        self.change_page(0)
        self.page_home.url_input.setText(url)
        self.page_home.inspect_url()

    def closeEvent(self, event):
        if hasattr(self, 'global_progress_timer') and self.global_progress_timer.isActive():
            self.global_progress_timer.stop()
        if hasattr(self, 'reconnection_timer') and self.reconnection_timer.isActive():
            self.reconnection_timer.stop()
        if hasattr(self, '_ipc_server'):
            self._ipc_server.close()
        self.tray_icon.hide()
        self.unregister_global_hotkey()
        run_in_background = False
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    run_in_background = data.get("run_in_background", False)
            except Exception:
                pass
        if run_in_background:
            executable = sys.executable
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            main_py = os.path.join(app_dir, "main.py")
            base_exec = os.path.basename(executable).lower()
            is_python = "python" in base_exec or base_exec in ["py.exe", "py"]
            if is_python:
                pythonw = executable.lower().replace("python.exe", "pythonw.exe")
                if os.path.exists(pythonw):
                    args = [pythonw, main_py, "--listener"]
                else:
                    args = [executable, main_py, "--listener"]
            else:
                args = [executable, "--listener"]
            try:
                import subprocess
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                subprocess.Popen(args, cwd=app_dir, creationflags=subprocess.CREATE_NO_WINDOW, startupinfo=startupinfo)
            except Exception:
                pass
        event.accept()

    def register_global_hotkey(self):
        if sys.platform != 'win32':
            return
        try:
            import ctypes
            hwnd = int(self.winId())
            res = ctypes.windll.user32.RegisterHotKey(hwnd, 4224, 0x0002, 0x44)           
            if res:
                self.hotkey_registered = True
        except Exception:
            pass

    def unregister_global_hotkey(self):
        if sys.platform != 'win32' or not self.hotkey_registered:
            return
        try:
            import ctypes
            hwnd = int(self.winId())
            ctypes.windll.user32.UnregisterHotKey(hwnd, 4224)
            self.hotkey_registered = False
        except Exception:
            pass

    def nativeEvent(self, eventType, message):
        if eventType == b"windows_generic_MSG" and sys.platform == 'win32':
            try:
                from ctypes import wintypes
                import ctypes
                msg = wintypes.MSG.from_address(int(message))
                if msg.message == 0x0312:            
                    if msg.wParam == 4224:
                        self.close()
                        return True, 0
            except Exception:
                pass
        return False, 0

    def on_clipboard_changed(self):
        clipboard_monitor = False
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    clipboard_monitor = data.get("clipboard_monitor", False)
            except Exception:
                pass
        if not clipboard_monitor:
            return
        text = QApplication.clipboard().text().strip()
        if not text:
            return
        if hasattr(self, 'last_monitored_url') and self.last_monitored_url == text:
            return
        is_dl_prefix = False
        normalized_text = text
        if text.startswith("dl"):
            is_dl_prefix = True
            normalized_text = text[2:].strip()
            if normalized_text.startswith(":"):
                normalized_text = normalized_text[1:].strip()
            if not normalized_text.startswith("http"):
                if "youtube.com" in normalized_text or "youtu.be" in normalized_text:
                    normalized_text = "https://" + normalized_text
        is_youtube = ("youtu.be/" in normalized_text or 
                      "youtube.com/watch" in normalized_text or 
                      "youtube.com/playlist" in normalized_text or
                      "youtube.com/shorts" in normalized_text)
        if is_youtube:
            self.last_monitored_url = text
            if is_dl_prefix:
                self.handle_incoming_url(normalized_text)
            else:
                data = {}
                if os.path.exists(self.settings_file):
                    try:
                        with open(self.settings_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                    except Exception:
                        pass
                links = data.get("collected_links", [])
                if normalized_text not in links:
                    links.append(normalized_text)
                    data["collected_links"] = links
                    try:
                        with open(self.settings_file, 'w', encoding='utf-8') as f:
                            json.dump(data, f, ensure_ascii=False, indent=4)
                    except Exception:
                        pass
                self.toast = InteractiveToast(
                    tr("clipboard_toast_title", "Download Detected"),
                    tr("toast_link_saved", "This link has been saved. Do you want to download it now?"),
                    normalized_text,
                    self.handle_incoming_url,
                    self
                )
                self.toast.show()
