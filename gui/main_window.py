import os
import sys
import json
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QStackedWidget, QApplication, QSystemTrayIcon
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QFont

# استدعاء الصفحات الجديدة بعد الفصل
from gui.pages.home_page import HomePage
from gui.pages.downloads_page import DownloadsPage
from gui.pages.history_page import HistoryPage
from gui.pages.settings_page import SettingsPage
from core.downloader import DownloadWorker
from utils.helpers import resource_path, get_colored_icon, get_current_theme_color
from utils.locales import tr  # 💡 استيراد محرك الترجمة السحري
from utils.theme import get_style_sheet  # 💡 استيراد محرك الثيمات الديناميكي الجديد

class VideoDownloader(QWidget):
    def __init__(self):
        super().__init__()
        self.is_playlist_mode = False
        self.selected_playlist_entries = []
        self.settings_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'settings.json')
        self.last_save_dir = self.load_settings()
        self.sidebar_expanded = True  # القائمة تبدأ مفتوحة افتراضياً
        self.initUI()

    def initUI(self):
        self.setWindowTitle('AHS-MediaDL')
        self.setWindowIcon(QIcon(resource_path(os.path.join('assets', 'icon.ico'))))
        self.resize(880, 560) 
        self.setMinimumSize(700, 480)

        # تحميل الحد الأقصى للملفات المتزامنة من الإعدادات بدلاً من الرقم الثابت 3
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

        # تهيئة أيقونة النظام للإشعارات
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(resource_path(os.path.join('assets', 'icon.ico'))))
        self.tray_icon.show()

        # 1️⃣ الـ Stack الرئيسي الأعلى للتطبيق ككل (للفصل التام لشاشة الإعدادات)
        window_layout = QVBoxLayout(self)
        window_layout.setContentsMargins(0, 0, 0, 0)
        window_layout.setSpacing(0)

        self.main_stack = QStackedWidget()
        window_layout.addWidget(self.main_stack)

        # 2️⃣ حاوية الواجهة الرئيسية (التي تحتوي على القائمة الجانبية والمحتوى معاً)
        self.main_app_widget = QWidget()
        app_layout = QHBoxLayout(self.main_app_widget)
        app_layout.setContentsMargins(0, 0, 0, 0)
        app_layout.setSpacing(0)

        # --- القائمة الجانبية المرنة (Navigation Rail) ---
        self.sidebar = QWidget()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setStyleSheet("QWidget#Sidebar { border-right: 1px solid rgba(128, 128, 128, 0.2); }")
        self.sidebar.setFixedWidth(180) 
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(5, 5, 5, 5)
        sidebar_layout.setSpacing(10)

        # رأس القائمة الجانبية (Header Layout) - شعار التطبيق + الاسم + زر الـ Collapse
        self.header_widget = QWidget()
        self.header_widget.setFixedHeight(45)
        self.header_layout = QHBoxLayout(self.header_widget)
        self.header_layout.setContentsMargins(5, 0, 5, 0)
        self.header_layout.setSpacing(8)
        
        # زر شعار التطبيق
        self.btn_logo = QPushButton()
        self.btn_logo.setIcon(QIcon(resource_path("assets/icon.ico")))
        self.btn_logo.setIconSize(QSize(32, 32))
        self.btn_logo.setFixedSize(32, 32)
        self.btn_logo.setFlat(True)
        self.btn_logo.setStyleSheet("background: transparent; border: none; padding: 0px;")
        self.btn_logo.clicked.connect(self.logo_clicked)
        self.header_layout.addWidget(self.btn_logo)
        
        # اسم التطبيق MediaDL بلون الغروب البرتقالي المحمر المطابق للشعار تماماً
        self.logo_text = QLabel("MediaDL")
        self.logo_text.setStyleSheet("color: #ff5e3a; font-size: 16px; font-weight: bold; background: transparent; border: none;")
        self.header_layout.addWidget(self.logo_text)
        
        from PyQt6.QtWidgets import QSizePolicy
        self.header_spacer = QWidget()
        self.header_spacer.setStyleSheet("background: transparent; border: none;")
        self.header_spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.header_layout.addWidget(self.header_spacer)
        
        # زر إغلاق/فتح القائمة الجانبية (Hamburger/Collapse)
        self.btn_menu = QPushButton()
        self.btn_menu.setObjectName("btn_menu")
        self.btn_menu.setIcon(get_colored_icon("assets/icons/collapse.svg", get_current_theme_color()))
        self.btn_menu.setIconSize(QSize(18, 18))
        self.btn_menu.setFixedSize(30, 30)
        self.btn_menu.clicked.connect(self.toggle_sidebar)
        self.header_layout.addWidget(self.btn_menu)
        
        sidebar_layout.addWidget(self.header_widget)

        # ربط النصوص بدالة tr() مباشرة مع وضع الأيقونات المخصصة والملونة ديناميكياً
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
        sidebar_layout.addSpacing(15)  # رفع زر الإعدادات قليلاً عن الأسفل لإعطاء مظهر متوازن ومريح للعين

        app_layout.addWidget(self.sidebar)

        # --- منطقة المحتوى الرئيسي الداخلي ---
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(10, 10, 10, 10)

        self.pages_stack = QStackedWidget()
        content_layout.addWidget(self.pages_stack)
        app_layout.addWidget(content_container)

        # إنشاء الصفحات البرمجية وتمرير المحاذاة
        self.page_home = HomePage(self) 
        self.page_downloads = DownloadsPage(self) 
        self.page_history = HistoryPage(self)
        self.page_settings = SettingsPage(self) 
        self.cards_layout = self.page_downloads.cards_layout 
        
        # إضافة الصفحات العادية للـ Stack الداخلي بجانب الـ Sidebar
        self.pages_stack.addWidget(self.page_home)
        self.pages_stack.addWidget(self.page_downloads)
        self.pages_stack.addWidget(self.page_history)
        
        # إضافة المكونات الكبرى للـ Stack الرئيسي الأعلى للفصل الكامل
        self.main_stack.addWidget(self.main_app_widget) # صفحة 0: التطبيق كاملاً بالـ Sidebar
        self.main_stack.addWidget(self.page_settings)   # صفحة 1: الإعدادات منفصلة ملء الشاشة
        
        # قراءة وتطبيق المظهر الكامل المحفوظ تلقائياً عند إقلاع التطبيق
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.apply_appearance(data.get("theme", "auto"), data.get("font_family", "System Default"), data.get("font_size", 12))
            except Exception:
                pass

        self.change_page(0) 

    def logo_clicked(self):
        self.toggle_sidebar()

    def toggle_sidebar(self):
        icon_color = get_current_theme_color()
        is_rtl = (self.layoutDirection() == Qt.LayoutDirection.RightToLeft)
        if self.sidebar_expanded:
            self.sidebar.setFixedWidth(60)
            self.logo_text.hide()
            self.btn_logo.show()       # 💡 تعديل: إظهار أيقونة الشعار عند غلق القائمة
            self.header_spacer.hide()
            self.btn_menu.hide()       # 💡 تعديل: إخفاء زر الهامبرغر ليحل الشعار محله تماماً
            self.btn_nav_home.setText("")
            self.btn_nav_downloads.setText("")
            self.btn_nav_history.setText("")
            self.btn_nav_settings.setText("")
            self.header_layout.setContentsMargins(0, 0, 0, 0)
            self.header_layout.setAlignment(self.btn_logo, Qt.AlignmentFlag.AlignCenter) # 💡 تعديل: سنترة الشعار في الـ 60 بكسل
            
            self.sidebar_expanded = False
        else:
            self.sidebar.setFixedWidth(180)
            self.logo_text.show()
            self.btn_logo.show()
            self.header_spacer.show()
            self.btn_menu.show()       # 💡 تعديل: إعادة إظهار زر الهامبرغر عند فتح القائمة
            self.btn_nav_home.setText(tr("nav_home"))
            self.btn_nav_downloads.setText(tr("nav_downloads"))
            self.btn_nav_history.setText(tr("nav_history"))
            self.btn_nav_settings.setText(tr("nav_settings"))
            self.header_layout.setContentsMargins(5, 0, 5, 0)
            
            # 💡 تعديل: إعادة ضبط محاذاة العناصر للوضع العمودي الطبيعي داخل الـ QHBoxLayout
            self.header_layout.setAlignment(self.btn_logo, Qt.AlignmentFlag.AlignVCenter)
            self.header_layout.setAlignment(self.btn_menu, Qt.AlignmentFlag.AlignVCenter)
            
            collapse_icon = "expand.svg" if is_rtl else "collapse.svg"
            self.btn_menu.setIcon(get_colored_icon(f"assets/icons/{collapse_icon}", icon_color))
            self.sidebar_expanded = True

    def change_page(self, index):
        if index == 3:
            # 💡 تفعيل وضع ملء الشاشة للإعدادات وإخفاء كل شيء آخر تلقائياً
            self.main_stack.setCurrentIndex(1)
            self.btn_nav_settings.setChecked(True)
            self.btn_nav_home.setChecked(False)
            self.btn_nav_downloads.setChecked(False)
            self.btn_nav_history.setChecked(False)
        else:
            # 💡 العودة للوضع الطبيعي وإظهار القائمة الجانبية والتنقل داخلياً
            self.main_stack.setCurrentIndex(0)
            self.pages_stack.setCurrentIndex(index)
            
            self.btn_nav_home.setChecked(index == 0)
            self.btn_nav_downloads.setChecked(index == 1)
            self.btn_nav_history.setChecked(index == 2)
            self.btn_nav_settings.setChecked(False)
            
            if index == 2 and hasattr(self, 'page_history'):
                self.page_history.load_history_ui()

    def load_settings(self):
        os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
        if os.path.exists(self.settings_file):
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
        # نقرأ الملف القديم أولاً لو موجود عشان نحافظ على إعدادات اللغة والإشعارات
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception:
                pass
        
        # نعدل فقط مسار التنزيل الأخير
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

                # فصل الإشارات فوراً لتفادي تحديث الواجهة أثناء الإنهاء
                try:
                    old_worker.progress_signal.disconnect()
                    old_worker.status_signal.disconnect()
                    old_worker.finished_signal.disconnect()
                    old_worker.finished.disconnect(self.on_worker_finished)
                except:
                    pass

                # تدمير الخيط بأمان: إذا كان يعمل نلغيه ونربطه بـ deleteLater عند اكتمال توقفه الطبيعي
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

        self.waiting_workers.append(worker)
        self.process_queue()

    def process_queue(self):
        while len(self.active_workers) < self.max_concurrent and self.waiting_workers:
            worker = self.waiting_workers.pop(0) 
            self.active_workers.append(worker)   
            worker.finished.connect(self.on_worker_finished)
            worker.start() 
        self.update_active_speed_limits()

    def on_worker_finished(self):
        worker = self.sender() 
        if worker in self.active_workers:
            self.active_workers.remove(worker) 
        worker.deleteLater()
        self.update_active_speed_limits()
        self.process_queue()

    def handle_subtitle_notification(self, type_noti, title, lang_name):
        """ 🔔 معالجة إشعارات الترجمة لقوائم التشغيل بصورة غير حازرة للتحميل (Non-blocking) """
        from PyQt6.QtWidgets import QMessageBox
        
        # 1. تحديد الرسائل بناءً على نوع الإشعار واللغة المحددة
        if type_noti == "secondary":
            toast_msg = tr("sub_secondary_dialog_msg").format(lang=lang_name, title=title)
            tray_msg = f"Downloaded in secondary language ({lang_name}) for: {title}"
        elif type_noti == "fallback":
            toast_msg = tr("sub_fallback_dialog_msg").format(lang=lang_name, title=title)
            tray_msg = f"Downloaded fallback original subtitle ({lang_name}) for: {title}"
        elif type_noti == "none":
            toast_msg = tr("sub_none_dialog_msg").format(title=title)
            tray_msg = f"No suitable subtitles found for: {title}"
        else:
            return

        # 2. إرسال إشعار سطح المكتب (السيستم تراي) ليعلم المستخدم حتى لو التطبيق مصغر
        self.show_notification(tr("sub_report_title", "Subtitle Download Report"), tray_msg)

        # 3. إظهار نافذة تقرير في التطبيق غير حاجزة (Non-modal Dialog)
        # نستخدم self كـ parent لتبقى النافذة معلقة فوق التطبيق، ونستدعي show() بدلاً من exec() لعدم تجميد التحميل
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(tr("sub_report_title", "Subtitle Download Report"))
        msg_box.setText(toast_msg)
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.button(QMessageBox.StandardButton.Ok).setText(tr("btn_done", "Done"))
        msg_box.show()

    def show_notification(self, title, message):
        """ إظهار إشعار سطح المكتب للمستخدم عند اكتمال التنزيل (إذا تم تفعيلها) """
        notifications_enabled = True
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    notifications_enabled = data.get("notifications", True)
            except Exception:
                pass
                
        if notifications_enabled:
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
        
        # 1. تحديث الخط والحجم عالمياً في التطبيق
        if font_family == "System Default":
            font = QApplication.font()
            font.setPointSize(font_size)
        else:
            font = QFont(font_family, font_size)
        QApplication.setFont(font)

        # 2. تحديد اتجاه واجهة المستخدم بناءً على اللغة المحددة
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

        # 3. جلب الـ QSS المولد ديناميكياً من ملف الـ theme وتطبيقه فوراً
        try:
            qss_content = get_style_sheet(theme_name, font_family, font_size, is_rtl=is_rtl)
            self.setStyleSheet(qss_content)
        except Exception:
            pass

        # 4. Update dynamic icon colors to match the chosen theme mode
        actual_theme = theme_name
        if theme_name == "auto":
            from PyQt6.QtGui import QGuiApplication
            scheme = QGuiApplication.styleHints().colorScheme()
            actual_theme = "dark" if scheme == Qt.ColorScheme.Dark else "light"
            
        icon_color = "#f1f5f9" if actual_theme == "dark" else "#0f172a"
        
        # Navigation Sidebar Buttons
        self.btn_nav_home.setIcon(get_colored_icon("assets/icons/home.svg", icon_color))
        self.btn_nav_downloads.setIcon(get_colored_icon("assets/icons/download.svg", icon_color))
        self.btn_nav_history.setIcon(get_colored_icon("assets/icons/history.svg", icon_color))
        self.btn_nav_settings.setIcon(get_colored_icon("assets/icons/settings.svg", icon_color))
        
        menu_icon = "assets/icons/collapse.svg" if self.sidebar_expanded else "assets/icons/expand.svg"
        self.btn_menu.setIcon(get_colored_icon(menu_icon, icon_color))
        
        # Propagate theme changes to pages and cards
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
            
        # إعادة تنشيط ومعالجة الطابور بناءً على الرقم الأقصى الجديد
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
        
        # تصفية فقط العمال النشطين (الذين لم يتم إيقافهم مؤقتاً)
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