"""
Main Window — Slim sidebar shell that hosts all pages via QStackedWidget.
"""
import os
import sys
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QFrame, QStackedWidget, QButtonGroup)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QIcon

from gui.pages.home_page import HomePage
from gui.pages.downloads_page import DownloadsPage
from gui.pages.history_page import HistoryPage
from gui.pages.settings_page import SettingsPage
from gui.widgets import ToastNotification
from data.settings import app_config
from utils import helpers


class DownloaderApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(helpers.APP_TITLE)
        self.resize(950, 700)
        
        # Dynamic window icon paths
        assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
        icons_dir = os.path.join(assets_dir, "icons")
        ico_path = os.path.join(assets_dir, "icon.ico")
        logo_path = os.path.join(assets_dir, "logo.png")
        icon_path = ico_path if os.path.exists(ico_path) else logo_path
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # Main Layout: [ Sidebar | Pages Stack ]
        self.main_h_layout = QHBoxLayout(self)
        self.main_h_layout.setContentsMargins(0, 0, 0, 0)
        self.main_h_layout.setSpacing(0)
        
        # ──────────────────────────────────────────
        #  1. SIDEBAR PANEL
        # ──────────────────────────────────────────
        self.sidebar_frame = QFrame()
        self.sidebar_frame.setObjectName("Sidebar")
        self.sidebar_frame.setFixedWidth(220)
        self.sidebar_layout = QVBoxLayout(self.sidebar_frame)
        self.sidebar_layout.setContentsMargins(12, 24, 12, 24)
        self.sidebar_layout.setSpacing(10)
        
        # Brand Logo Header
        self.brand_layout = QHBoxLayout()
        self.brand_layout.setSpacing(10)
        self.brand_layout.setContentsMargins(0, 0, 0, 0)
        
        self.brand_logo = QLabel()
        self.brand_logo.setFixedSize(38, 38)
        self.brand_logo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.brand_logo.mousePressEvent = lambda e: self.toggle_sidebar()
        if os.path.exists(icon_path):
            logo_pix = QPixmap(icon_path)
            self.brand_logo.setPixmap(logo_pix.scaled(38, 38, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        
        self.brand_title = QLabel("MediaDL")
        self.brand_title.setObjectName("heading")
        self.brand_title.setStyleSheet("font-size: 14pt; font-weight: 800; color: #7c6af7;")
        
        self.btn_toggle_sidebar = QPushButton()
        self.btn_toggle_sidebar.setFixedSize(32, 32)
        self.btn_toggle_sidebar.setIconSize(QSize(18, 18))
        self.btn_toggle_sidebar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_sidebar.setIcon(helpers.get_theme_icon("collapse.svg"))
        self.btn_toggle_sidebar.setToolTip("Collapse Sidebar" if not helpers.is_ar else "طي القائمة")
        self.btn_toggle_sidebar.setObjectName("SidebarToggleButton")
        self.btn_toggle_sidebar.setStyleSheet("background: transparent; border: none;")
        self.btn_toggle_sidebar.clicked.connect(self.toggle_sidebar)
        
        self.brand_layout.addWidget(self.brand_logo)
        self.brand_layout.addWidget(self.brand_title)
        self.brand_layout.addStretch()
        self.brand_layout.addWidget(self.btn_toggle_sidebar)
        self.sidebar_layout.addLayout(self.brand_layout)
        
        # Separator line
        self.line = QFrame()
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)
        self.line.setStyleSheet("background-color: rgba(255,255,255,0.05); max-height: 1px; margin: 15px 0;")
        self.sidebar_layout.addWidget(self.line)
        
        # Checkable Sidebar Buttons loaded with SVGs
        self.btn_home = QPushButton("  " + helpers.TAB_ADD)
        self.btn_home.setObjectName("SidebarButton")
        self.btn_home.setCheckable(True)
        self.btn_home.setChecked(True)
        self.btn_home.setIcon(helpers.get_theme_icon("home.svg"))
        self.sidebar_layout.addWidget(self.btn_home)
        
        self.btn_downloads = QPushButton("  " + helpers.TAB_QUEUE)
        self.btn_downloads.setObjectName("SidebarButton")
        self.btn_downloads.setCheckable(True)
        self.btn_downloads.setIcon(helpers.get_theme_icon("download.svg"))
        self.sidebar_layout.addWidget(self.btn_downloads)
        
        self.btn_history = QPushButton("  " + ("سجل" if helpers.is_ar else "History"))
        self.btn_history.setObjectName("SidebarButton")
        self.btn_history.setCheckable(True)
        self.btn_history.setIcon(helpers.get_theme_icon("history.svg"))
        self.sidebar_layout.addWidget(self.btn_history)
        
        # Sidebar Spacer (anchors settings to bottom)
        self.sidebar_layout.addStretch()
        
        # Bottom Anchor Settings Button
        self.btn_settings = QPushButton("  " + helpers.BTN_SETTINGS)
        self.btn_settings.setObjectName("SidebarButton")
        self.btn_settings.setCheckable(True)
        self.btn_settings.setIcon(helpers.get_theme_icon("settings.svg"))
        self.sidebar_layout.addWidget(self.btn_settings)
        
        # Mutually exclusive checking
        self.sidebar_group = QButtonGroup(self)
        self.sidebar_group.addButton(self.btn_home, 0)
        self.sidebar_group.addButton(self.btn_downloads, 1)
        self.sidebar_group.addButton(self.btn_history, 2)
        self.sidebar_group.addButton(self.btn_settings, 3)
        self.sidebar_group.buttonClicked.connect(self.on_sidebar_nav_clicked)
        
        # Hidden "Restart Now" button appearing when restart is pending
        self.btn_restart_pending = QPushButton("  " + ("إعادة التشغيل" if helpers.is_ar else "Restart Now"))
        self.btn_restart_pending.setIcon(helpers.get_theme_icon("restart.svg"))
        self.btn_restart_pending.setObjectName("primary")
        self.btn_restart_pending.setStyleSheet("background-color: #e67e22; color: white; padding: 10px; border-radius: 8px;")
        self.btn_restart_pending.clicked.connect(self.restart_app)
        self.btn_restart_pending.hide()
        self.sidebar_layout.addWidget(self.btn_restart_pending)
        
        self.main_h_layout.addWidget(self.sidebar_frame)
        
        # ──────────────────────────────────────────
        #  2. PAGES CONTAINER (Stacked Widget)
        # ──────────────────────────────────────────
        self.pages_stack = QStackedWidget()
        self.main_h_layout.addWidget(self.pages_stack, stretch=1)
        
        # Initialize Pages
        self.home_page = HomePage(self)
        self.home_page.add_to_queue_signal.connect(self.on_add_to_queue)
        self.home_page.switch_to_downloads_signal.connect(self.switch_to_downloads)
        
        self.downloads_page = DownloadsPage(self)
        self.history_page = HistoryPage(self)
        
        self.settings_page = SettingsPage(self)
        self.settings_page.restart_required_signal.connect(self.handle_restart_needed)
        
        # Mount pages into stack
        self.pages_stack.addWidget(self.home_page)      # Index 0
        self.pages_stack.addWidget(self.downloads_page)  # Index 1
        self.pages_stack.addWidget(self.history_page)    # Index 2
        self.pages_stack.addWidget(self.settings_page)   # Index 3

    # ──────────────────────────────────────────────
    #  Sidebar Navigation
    # ──────────────────────────────────────────────

    def on_sidebar_nav_clicked(self, button):
        button_id = self.sidebar_group.id(button)
        self.pages_stack.setCurrentIndex(button_id)

    def switch_to_downloads(self):
        self.btn_downloads.setChecked(True)
        self.pages_stack.setCurrentIndex(1)

    # ──────────────────────────────────────────────
    #  Queue Bridge (Home → Downloads)
    # ──────────────────────────────────────────────

    def on_add_to_queue(self, downloads):
        for dl in downloads:
            self.downloads_page.add_queue_item(
                dl['url'], dl['title'], dl.get('thumb_data'),
                dl['format_id'], dl.get('sub_langs', []),
                dl.get('subs_only', False), dl.get('embed_subs', False),
                dl.get('custom_save_dir')
            )
        self.downloads_page.manage_queue()

    # ──────────────────────────────────────────────
    #  Restart & Toast Notifications
    # ──────────────────────────────────────────────

    def handle_restart_needed(self, message):
        if message:
            self.show_toast_notification(message)
            self.btn_restart_pending.show()
        else:
            self.btn_restart_pending.hide()

    def show_toast_notification(self, message):
        toast = ToastNotification(message, self)
        # Position toast overlay at bottom right
        toast.move(self.width() - toast.width() - 20, self.height() - toast.height() - 20)
        toast.show()

    def restart_app(self):
        # Gracefully restart application
        os.execl(sys.executable, sys.executable, *sys.argv)

    def refresh_theme_icons(self):
        self.btn_home.setIcon(helpers.get_theme_icon("home.svg"))
        self.btn_downloads.setIcon(helpers.get_theme_icon("download.svg"))
        self.btn_history.setIcon(helpers.get_theme_icon("history.svg"))
        self.btn_settings.setIcon(helpers.get_theme_icon("settings.svg"))
        self.btn_restart_pending.setIcon(helpers.get_theme_icon("restart.svg"))
        
        # Refresh the sidebar toggle icon
        icon_name = "expand.svg" if getattr(self, 'sidebar_collapsed', False) else "collapse.svg"
        self.btn_toggle_sidebar.setIcon(helpers.get_theme_icon(icon_name))
        
        # Delegate down to all active pages
        self.home_page.refresh_theme_icons()
        self.downloads_page.refresh_theme_icons()
        self.history_page.refresh_theme_icons()
        self.settings_page.refresh_theme_icons()

    def toggle_sidebar(self):
        self.sidebar_collapsed = not getattr(self, 'sidebar_collapsed', False)
        if self.sidebar_collapsed:
            self.sidebar_frame.setFixedWidth(70)
            self.brand_title.hide()
            self.btn_toggle_sidebar.hide()
            
            # Center logo
            self.brand_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Hide text on all sidebar buttons
            self.btn_home.setText("")
            self.btn_downloads.setText("")
            self.btn_history.setText("")
            self.btn_settings.setText("")
            self.btn_restart_pending.setText("")
            
            # Center the icons
            self.btn_home.setStyleSheet("padding: 10px 0; text-align: center; border-left: none;")
            self.btn_downloads.setStyleSheet("padding: 10px 0; text-align: center; border-left: none;")
            self.btn_history.setStyleSheet("padding: 10px 0; text-align: center; border-left: none;")
            self.btn_settings.setStyleSheet("padding: 10px 0; text-align: center; border-left: none;")
            self.btn_restart_pending.setStyleSheet("padding: 10px 0; text-align: center; border-left: none;")
        else:
            self.sidebar_frame.setFixedWidth(220)
            self.brand_title.show()
            self.btn_toggle_sidebar.show()
            
            # Left/Right alignment
            self.brand_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
            
            # Restore text
            self.btn_home.setText("  " + helpers.TAB_ADD)
            self.btn_downloads.setText("  " + helpers.TAB_QUEUE)
            self.btn_history.setText("  " + ("سجل" if helpers.is_ar else "History"))
            self.btn_settings.setText("  " + helpers.BTN_SETTINGS)
            self.btn_restart_pending.setText("  " + ("إعادة التشغيل" if helpers.is_ar else "Restart Now"))
            
            # Restore styling
            self.btn_home.setStyleSheet("")
            self.btn_downloads.setStyleSheet("")
            self.btn_history.setStyleSheet("")
            self.btn_settings.setStyleSheet("")
            self.btn_restart_pending.setStyleSheet("")
